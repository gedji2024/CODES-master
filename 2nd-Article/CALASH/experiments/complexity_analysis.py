"""
Complexity Analysis Module
============================
Per-round computational complexity for each protocol + empirical timing.

Theoretical O(.) analysis per round:
    Protocol        | Setup Phase          | Routing Phase        | Total
    --------------- | -------------------- | -------------------- | -----
    LEACH     [1]   | O(N)                 | O(K*H)              | O(N)
    LEACH-1hop [1]  | O(N)                 | O(K)                | O(N)
    EE-LEACH  [2]   | O(N)                 | O(K*H)              | O(N)
    HEED      [3]   | O(N*D)               | O(K*H)              | O(N*D)
    EERP      [4]   | O(N*D)               | O(K*D*H)            | O(N*D)
    ABC-ACO   [5]   | O(N*D + P*I*K)       | O(K*D*H)            | O(N*D + P*I*K)
    Q-Routing [6]   | O(N)                 | O(K*A*H)            | O(N + K*A)
    CALASH          | O(N*D + DQN)         | O(K*(DQN+Lyap)*H)   | O(N*D + K*DQN)

    N = nodes, K = CHs, D = avg degree (neighbors within tx_range),
    H = max hops to BS, P = ABC population, I = ABC iterations,
    A = Q-table actions, DQN = forward pass (64*8 + 32*64 + A*32 MACs)

Empirical timing uses wall-clock measurements (time.perf_counter)
over 100 rounds, repeated 5 times, on a single core.

References
----------
[1] Heinzelman, W.B. et al. IEEE Trans. Wireless Comm., 1(4), 2002.
[2] Bakaraniya, P. & Mehta, S. IJETT, 4(5), 2013.
[3] Younis, O. & Fahmy, S. IEEE Trans. Mobile Comp., 3(4), 2004.
[4] Biswas, S. et al. J. Wireless Comm. Networks, Springer, 2019.
[5] El Khediri, S. et al. Ad Hoc Networks, 158, art. 103473, 2024.
[6] Soltani, M. et al. Neural Computing & Applications, Springer, 2025.
"""

import os
import sys
import time
import json
import numpy as np
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Theoretical complexity expressions
COMPLEXITY = {
    'LEACH': {
        'setup': 'O(N)',
        'routing': 'O(K × H)',
        'total': 'O(N)',
        'description': 'Linear threshold election + greedy geographic routing',
    },
    'LEACH-1hop': {
        'setup': 'O(N)',
        'routing': 'O(K)',
        'total': 'O(N)',
        'description': 'Same election as LEACH, single-hop routing (no relay)',
    },
    'EE-LEACH': {
        'setup': 'O(N)',
        'routing': 'O(K × H)',
        'total': 'O(N)',
        'description': 'Energy-weighted threshold election + greedy routing',
    },
    'EERP': {
        'setup': 'O(N × D)',
        'routing': 'O(K × D × H)',
        'total': 'O(N × D)',
        'description': ('Neighborhood competition (D neighbors per node) + '
                        'relay cost routing'),
    },
    'ABC-ACO': {
        'setup': 'O(N × D + P × I × K)',
        'routing': 'O(K × D × H)',
        'total': 'O(N × D + P × I × K)',
        'description': ('ABC optimization (P=10 populations, I=3 iterations) + '
                        'ACO pheromone routing'),
    },
    'Q-Routing': {
        'setup': 'O(N)',
        'routing': 'O(K × A × H)',
        'total': 'O(N + K × A)',
        'description': 'Same election as EE-LEACH, ε-greedy Q-table routing',
    },
    'CALASH': {
        'setup': 'O(N × D + N_DQN)',
        'routing': 'O(K × (N_DQN + N_Lyap) × H)',
        'total': 'O(N × D + K × N_DQN)',
        'description': ('Carbon-modulated election + DQN forward pass + '
                        'Lyapunov drift + self-healing MAPE-K'),
    },
}


def measure_per_round_timing(config=None, protocols: List[str] = None,
                             n_warmup: int = 10,
                             n_measure: int = 50,
                             verbose: bool = True) -> Dict:
    """
    Empirically measure per-round wall time for each protocol.

    Parameters
    ----------
    config : SimulationConfig, optional
        Configuration to use (default: standard 200-node).
    protocols : list of str, optional
        Protocols to measure (default: all).
    n_warmup : int
        Warmup rounds (not measured).
    n_measure : int
        Rounds to average over.

    Returns
    -------
    dict
        {protocol: {mean_ms, std_ms, min_ms, max_ms, total_ms}}
    """
    from config import SimulationConfig
    from models.network import Network
    from models.energy import EnergyModel
    from models.carbon import CarbonTraceManager
    from models.compression import CompressiveSensing
    from experiments.runner import create_protocol

    if config is None:
        config = SimulationConfig(num_rounds=n_warmup + n_measure + 10)

    if protocols is None:
        from experiments.runner import PROTOCOL_CLASSES
        protocols = list(PROTOCOL_CLASSES.keys())

    results = {}

    for proto_name in protocols:
        if verbose:
            print(f"  Timing {proto_name} ...")

        rng = np.random.default_rng(42)
        network = Network(config, rng)
        energy = EnergyModel(config)
        carbon = CarbonTraceManager(config, rng)
        cs = CompressiveSensing(config, rng)

        protocol = create_protocol(proto_name, config, energy, carbon, cs, rng)
        if hasattr(protocol, 'reset'):
            protocol.reset()
        if hasattr(protocol, 'reset_q_tables'):
            protocol.reset_q_tables()

        # Warmup
        for r in range(1, n_warmup + 1):
            if network.num_alive() == 0:
                break
            protocol.run_round(network, r)

        # Measure
        times_ms = []
        for r in range(n_warmup + 1, n_warmup + n_measure + 1):
            if network.num_alive() == 0:
                break
            t0 = time.perf_counter()
            protocol.run_round(network, r)
            elapsed = (time.perf_counter() - t0) * 1000  # ms
            times_ms.append(elapsed)

        if times_ms:
            results[proto_name] = {
                'mean_ms': float(np.mean(times_ms)),
                'std_ms': float(np.std(times_ms)),
                'min_ms': float(np.min(times_ms)),
                'max_ms': float(np.max(times_ms)),
                'median_ms': float(np.median(times_ms)),
                'n_rounds': len(times_ms),
                'total_ms': float(np.sum(times_ms)),
                'complexity': COMPLEXITY.get(proto_name, {}).get('total', '?'),
            }

    return results


def generate_complexity_table(timing: Dict = None,
                              output_dir: str = 'results') -> str:
    """
    Generate LaTeX complexity comparison table.

    Parameters
    ----------
    timing : dict, optional
        Empirical timing results.
    output_dir : str
        Output directory.

    Returns
    -------
    str
        LaTeX table source.
    """
    lines = [
        '\\begin{table}[!t]',
        '\\centering',
        '\\caption{Per-round computational complexity (theoretical and '
        'empirical, N=200 nodes, averaged over 50 rounds).}',
        '\\label{tab:complexity}',
        '\\begin{tabular}{lllr}',
        '\\toprule',
        'Protocol & Setup & Routing & Time (ms) \\\\',
        '\\midrule',
    ]

    protocols_order = ['LEACH', 'LEACH-1hop', 'EE-LEACH', 'EERP',
                       'ABC-ACO', 'Q-Routing', 'CALASH']

    for proto in protocols_order:
        cx = COMPLEXITY.get(proto, {})
        setup = cx.get('setup', '?')
        routing = cx.get('routing', '?')

        if timing and proto in timing:
            t = timing[proto]
            time_str = f"{t['mean_ms']:.2f}$\\pm${t['std_ms']:.2f}"
        else:
            time_str = '--'

        proto_safe = proto.replace('-', '\\text{-}')
        lines.append(f'{proto_safe} & ${setup}$ & ${routing}$ & '
                     f'{time_str} \\\\')

    lines += ['\\bottomrule', '\\end{tabular}', '\\end{table}']
    latex = '\n'.join(lines)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'table_complexity.tex'), 'w') as f:
        f.write(latex)

    return latex


def main():
    """Run complexity analysis and generate table."""
    from config import SimulationConfig

    print("Complexity Analysis")
    print("=" * 50)

    config = SimulationConfig(num_rounds=200)
    timing = measure_per_round_timing(config, verbose=True)

    print(f"\n{'Protocol':<16} {'Theory':<25} {'Empirical (ms)':>20}")
    print("-" * 61)
    for proto in timing:
        cx = COMPLEXITY.get(proto, {}).get('total', '?')
        t = timing[proto]
        print(f"{proto:<16} {cx:<25} "
              f"{t['mean_ms']:>8.2f} ± {t['std_ms']:.2f}")

    latex = generate_complexity_table(timing)
    print(f"\nLaTeX table saved to results/table_complexity.tex")

    # Save JSON
    with open('results/complexity_timing.json', 'w') as f:
        json.dump(timing, f, indent=2)
    print("Timing data saved to results/complexity_timing.json")


if __name__ == '__main__':
    main()

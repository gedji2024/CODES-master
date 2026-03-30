import argparse
import os
import time
from types import SimpleNamespace as SN
from typing import Optional, Tuple


def _now():
    try:
        return time.perf_counter_ns()
    except Exception:
        return int(time.perf_counter() * 1e9)


def _kb(bytes_val: int, base: int = 1024) -> float:
    return bytes_val / float(base)


def _measure_peak_memory_and_latency(run_fn, warmup: int = 3, iters: int = 30, base: int = 1024) -> Tuple[float, float]:
    """Return (avg_latency_ms, peak_kb) for running run_fn()."""
    import tracemalloc
    # Warmup
    for _ in range(max(0, warmup)):
        run_fn()
    # Measure
    tracemalloc.start()
    t0 = _now()
    for _ in range(max(1, iters)):
        run_fn()
    t1 = _now()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total_ns = max(1, t1 - t0)
    avg_latency_ms = (total_ns / iters) / 1e6
    peak_kb = _kb(peak, base)
    return avg_latency_ms, peak_kb


def _maybe_energy_uj(latency_ms: float, avg_power_w: Optional[float]) -> Optional[float]:
    """Estimate energy (µJ) as power*latency if avg_power_w provided; else None."""
    if avg_power_w is None:
        return None
    joules = avg_power_w * (latency_ms / 1000.0)
    return joules * 1e6


# ---------------- EPyMARL: analytic MACs/FLOPs ----------------

def _qmix_macs(n_agents: int, state_dim: int, embed_dim: int, hypernet_embed: int) -> int:
    # Agent forward MACs per agent (fc1 + GRUCell + fc2) with dims fixed to hidden=64, input=66, actions=31
    # For generality, keep hidden=64 (as used in this repo). Adjust if needed.
    hidden = 64
    input_dim = 66  # obs 5 + last_action 31 + agent_id 30
    actions = 31
    per_agent = input_dim * hidden + 3 * (hidden * hidden + hidden * hidden) + hidden * actions
    agents_total = n_agents * per_agent

    # Mixer MACs (hypernets + small matmuls)
    E = embed_dim
    A = n_agents
    H = hypernet_embed
    S = state_dim
    # hyper_w_1: S->H and H->(E*A)
    mac_hyper_w1 = S * H + H * (E * A)
    # hyper_w_final: S->H and H->E
    mac_hyper_wfinal = S * H + H * E
    # hyper_b_1: S->E
    mac_hyper_b1 = S * E
    # V(s): S->E and E->1
    mac_V = S * E + E * 1
    # hidden bmm and final bmm
    mac_hidden_bmm = A * E
    mac_final_bmm = E * 1
    mixer_total = mac_hyper_w1 + mac_hyper_wfinal + mac_hyper_b1 + mac_V + mac_hidden_bmm + mac_final_bmm

    return agents_total + mixer_total


def _qtran_macs(n_agents: int, state_dim: int, rnn_hidden_dim: int, n_actions: int, embed_dim: int) -> int:
    # Agent forward as above (hidden=64, input=66, actions=31)
    hidden = rnn_hidden_dim
    input_dim = 66
    actions = n_actions
    per_agent = input_dim * hidden + 3 * (hidden * hidden + hidden * hidden) + hidden * actions
    agents_total = n_agents * per_agent

    # QTranBase (arch='qtran_paper', network_size='big')
    # action_encoding per agent: (hidden+actions)=ae_input -> ae_input -> ae_input with two linears
    ae_input = hidden + actions  # 64 + 31 = 95
    mac_action_enc_per_agent = ae_input * ae_input + ae_input * ae_input
    mac_action_enc = n_agents * mac_action_enc_per_agent

    # Q(s, sum_enc): input = state_dim + ae_input -> 64 -> 64 -> 64 -> 1
    q_in = state_dim + ae_input
    mac_Q = q_in * embed_dim + embed_dim * embed_dim + embed_dim * embed_dim + embed_dim * 1

    # V(s): state_dim -> 64 -> 64 -> 64 -> 1
    mac_V = state_dim * embed_dim + embed_dim * embed_dim + embed_dim * embed_dim + embed_dim * 1

    return agents_total + mac_action_enc + mac_Q + mac_V


# ---------------- EPyMARL: runtime benchmark ----------------

def _build_qmix_modules(n_agents: int, n_actions: int, state_dim: int) -> Tuple[object, object, SN]:
    import torch
    from modules.agents.rnn_agent import RNNAgent
    from modules.mixers.qmix import QMixer
    args = SN(hidden_dim=64, n_actions=n_actions, use_rnn=True,
              n_agents=n_agents, state_shape=state_dim, mixing_embed_dim=64,
              hypernet_layers=2, hypernet_embed=64)
    agent = RNNAgent(input_shape=66, args=args)
    mixer = QMixer(args)
    return agent, mixer, args


def _run_qmix_forward(agent, mixer, n_agents: int, state_dim: int):
    import torch
    # Single-sample, batched over agents
    x = torch.randn(n_agents, 66)
    h = agent.init_hidden().expand(n_agents, -1)
    q, h2 = agent(x, h)
    # agent_qs shape (n_agents) -> mixer expects (B, n_agents)
    agent_qs = q.unsqueeze(0).squeeze(-2)  # (1, n_agents, n_actions) -> reduce via max to per-agent q
    # Take max over actions per agent to simulate chosen action Qs
    agent_qs = agent_qs.max(dim=-1)[0]  # (1, n_agents)
    states = torch.randn(1, state_dim)
    _ = mixer(agent_qs, states)


def _build_qtran_module(n_agents: int, n_actions: int, state_dim: int) -> Tuple[object, SN]:
    from modules.mixers.qtran import QTranBase
    args = SN(n_agents=n_agents, n_actions=n_actions, state_shape=state_dim,
              qtran_arch="qtran_paper", network_size="big",
              mixing_embed_dim=64, rnn_hidden_dim=64)
    return QTranBase(args), args


def _run_qtran_forward(qtran, n_agents: int, n_actions: int, state_dim: int):
    import torch
    # Build a minimal dict-like batch
    class B:
        def __init__(self, state, actions_onehot, batch_size=1, max_seq_length=1):
            self._d = {"state": state, "actions_onehot": actions_onehot}
            self.batch_size = batch_size
            self.max_seq_length = max_seq_length
        def __getitem__(self, k):
            return self._d[k]

    bs, ts = 1, 1
    state = torch.randn(bs, ts, state_dim)
    actions_oh = torch.zeros(bs, ts, n_agents, n_actions)
    actions_idx = torch.randint(low=0, high=n_actions, size=(bs, ts, n_agents, 1))
    actions_oh.scatter_(3, actions_idx, 1.0)
    hidden_states = torch.randn(bs, ts, n_agents, 64)
    batch = B(state, actions_oh, bs, ts)
    _ = qtran(batch, hidden_states)


# ---------------- TSMixer: runtime benchmark ----------------

def _run_tsmixer_predict(model_name: str, input_chunk_length: int, features: int, series_count: int = 2):
    from darts import TimeSeries
    from darts.models import TSMixerModel
    import numpy as np
    # Load trained model
    model = TSMixerModel.load_from_checkpoint(model_name)
    # Build minimal synthetic multivariate series list
    length = input_chunk_length + 1
    series_list = []
    for _ in range(series_count):
        data = np.random.randn(length, features)
        s = TimeSeries.from_values(data)
        series_list.append(s)
    # Predict 1 step ahead
    _ = model.predict(series=series_list, n=1)


def main():
    parser = argparse.ArgumentParser(description="Benchmark inference: latency, peak RAM, MACs/FLOPs (where possible), and sizes.")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_qmix = sub.add_parser("qmix", help="Benchmark QMIX (agent + mixer)")
    p_qmix.add_argument("--n_agents", type=int, default=30)
    p_qmix.add_argument("--n_actions", type=int, default=31)
    p_qmix.add_argument("--state_dim", type=int, default=150)
    p_qmix.add_argument("--avg_power_w", type=float)
    p_qmix.add_argument("--base", type=int, default=1024, choices=[1000, 1024])

    p_qtran = sub.add_parser("qtran", help="Benchmark QTRAN (agent + mixer)")
    p_qtran.add_argument("--n_agents", type=int, default=30)
    p_qtran.add_argument("--n_actions", type=int, default=31)
    p_qtran.add_argument("--state_dim", type=int, default=150)
    p_qtran.add_argument("--avg_power_w", type=float)
    p_qtran.add_argument("--base", type=int, default=1024, choices=[1000, 1024])

    p_tsm = sub.add_parser("tsmixer", help="Benchmark TSMixer (Darts predict)")
    p_tsm.add_argument("--model_name", required=True)
    p_tsm.add_argument("--input_chunk_length", type=int, default=500)
    p_tsm.add_argument("--features", type=int, default=7)
    p_tsm.add_argument("--series_count", type=int, default=2)
    p_tsm.add_argument("--avg_power_w", type=float)
    p_tsm.add_argument("--base", type=int, default=1024, choices=[1000, 1024])

    args = parser.parse_args()

    if args.mode == "qmix":
        agent, mixer, a = _build_qmix_modules(args.n_agents, args.n_actions, args.state_dim)
        avg_ms, peak_kb = _measure_peak_memory_and_latency(lambda: _run_qmix_forward(agent, mixer, args.n_agents, args.state_dim))
        macs = _qmix_macs(args.n_agents, args.state_dim, embed_dim=64, hypernet_embed=64)
        flops = 2 * macs
        energy_uj = _maybe_energy_uj(avg_ms, args.avg_power_w)
        print("=== QMIX Inference ===")
        print(f"Latency (avg): {avg_ms:.3f} ms over 30 iters")
        print(f"Peak RAM (tracemalloc): {peak_kb:.2f} KB (base {args.base})")
        print(f"MACs (est.): {macs:,}")
        print(f"FLOPs (est., 2*MACs): {flops:,}")
        if energy_uj is not None:
            print(f"Energy per inference (est.): {energy_uj:.1f} µJ @ {args.avg_power_w} W")
        return

    if args.mode == "qtran":
        qtran, a = _build_qtran_module(args.n_agents, args.n_actions, args.state_dim)
        avg_ms, peak_kb = _measure_peak_memory_and_latency(lambda: _run_qtran_forward(qtran, args.n_agents, args.n_actions, args.state_dim))
        macs = _qtran_macs(args.n_agents, args.state_dim, rnn_hidden_dim=64, n_actions=args.n_actions, embed_dim=64)
        flops = 2 * macs
        energy_uj = _maybe_energy_uj(avg_ms, args.avg_power_w)
        print("=== QTRAN Inference ===")
        print(f"Latency (avg): {avg_ms:.3f} ms over 30 iters")
        print(f"Peak RAM (tracemalloc): {peak_kb:.2f} KB (base {args.base})")
        print(f"MACs (est.): {macs:,}")
        print(f"FLOPs (est., 2*MACs): {flops:,}")
        if energy_uj is not None:
            print(f"Energy per inference (est.): {energy_uj:.1f} µJ @ {args.avg_power_w} W")
        return

    if args.mode == "tsmixer":
        avg_ms, peak_kb = _measure_peak_memory_and_latency(
            lambda: _run_tsmixer_predict(args.model_name, args.input_chunk_length, args.features, args.series_count)
        )
        energy_uj = _maybe_energy_uj(avg_ms, args.avg_power_w)
        print("=== TSMixer Predict ===")
        print(f"Latency (avg): {avg_ms:.3f} ms over 30 iters (predict n=1)")
        print(f"Peak RAM (tracemalloc): {peak_kb:.2f} KB (base {args.base})")
        print("MACs/FLOPs: (use a FLOP profiler like thop if needed on model.model)")
        if energy_uj is not None:
            print(f"Energy per inference (est.): {energy_uj:.1f} µJ @ {args.avg_power_w} W")
        return


if __name__ == "__main__":
    main()

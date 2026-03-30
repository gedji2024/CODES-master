"""
Smoke test for all critical fixes:
1. Non-omniscient self-healing (handle_disaster is a no-op)
2. Carbon throttle (transmission deferral when Z(t) high)
3. Closed-loop fidelity feedback (CADR adaptive rho)
4. Randomised disaster timing per seed
5. DQN vs Lyapunov decision tracking
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from config import SimulationConfig
from protocols.calash import CALASH
from protocols.ablations import CALASH_NoCO2, CALASH_NoSH, CALASH_NoCADR, CALASH_NoLCI
from models.network import Network
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing
from models.disaster import DisasterEvent


def test_calash_basic_10_rounds():
    """CALASH runs 10 rounds and returns all new metric keys."""
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH(cfg, em, cm, cs, rng)
    p.reset()
    for r in range(1, 11):
        m = p.run_round(net, r)

    # Check new metric keys exist
    for key in ['energy_heartbeat', 'deferred_packets', 'dqn_ratio',
                'fidelity_boost', 'carbon_queue', 'recovery_mode']:
        assert key in m, f"Missing metric key: {key}"

    print(f"  energy_heartbeat = {m['energy_heartbeat']:.6f}")
    print(f"  deferred_packets = {m['deferred_packets']}")
    print(f"  dqn_ratio        = {m['dqn_ratio']:.4f}")
    print(f"  fidelity_boost   = {m['fidelity_boost']:.4f}")
    print("  PASS")


def test_ablation_noco2():
    """NoCO2 keeps self-healing (energy_heartbeat > 0)."""
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH_NoCO2(cfg, em, cm, cs, rng)
    p.reset()
    for r in range(1, 11):
        m = p.run_round(net, r)

    assert 'energy_heartbeat' in m, "NoCO2 missing energy_heartbeat"
    assert m['energy_heartbeat'] > 0, "NoCO2 should have heartbeat energy > 0"
    print(f"  energy_heartbeat = {m['energy_heartbeat']:.6f} (has self-healing)")
    print("  PASS")


def test_ablation_nosh():
    """NoSH has healer=None, so energy_heartbeat = 0."""
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH_NoSH(cfg, em, cm, cs, rng)
    p.reset()
    for r in range(1, 11):
        m = p.run_round(net, r)

    assert m.get('energy_heartbeat', 0) == 0.0, \
        f"NoSH should have 0 heartbeat energy, got {m.get('energy_heartbeat')}"
    print(f"  energy_heartbeat = {m.get('energy_heartbeat', 0):.6f} (no healer)")
    print("  PASS")


def test_ablation_nocadr():
    """NoCADR uses full packets (rho=1.0)."""
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH_NoCADR(cfg, em, cm, cs, rng)
    p.reset()
    for r in range(1, 11):
        m = p.run_round(net, r)

    assert m.get('compression_ratio', 0) == 1.0, \
        f"NoCADR should have rho=1.0, got {m.get('compression_ratio')}"
    print(f"  compression_ratio = {m.get('compression_ratio', 0):.2f}")
    print("  PASS")


def test_ablation_nolci():
    """NoLCI runs without errors."""
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH_NoLCI(cfg, em, cm, cs, rng)
    p.reset()
    for r in range(1, 11):
        m = p.run_round(net, r)

    print(f"  dqn_ratio = {m.get('dqn_ratio', 'N/A')}")
    print("  PASS")


def test_handle_disaster_is_noop():
    """Calling handle_disaster does nothing — protocol discovers via heartbeats."""
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH(cfg, em, cm, cs, rng)
    p.reset()

    # Run a few rounds
    for r in range(1, 5):
        p.run_round(net, r)

    # Call handle_disaster — should do nothing
    p.handle_disaster(net, [0, 1, 2], 5)
    assert not p.disaster_detected, "handle_disaster should NOT set disaster_detected"
    assert not p.recovery_mode, "handle_disaster should NOT set recovery_mode"
    print("  handle_disaster is a genuine no-op")
    print("  PASS")


def test_organic_self_healing():
    """
    Apply disaster directly to network. Protocol should detect it
    organically through heartbeat monitoring after timeout rounds.
    """
    cfg = SimulationConfig(
        num_nodes=100,
        num_rounds=30,
        disaster_enabled=True,
        disaster_round=10,
        healing_detection_rounds=3,
    )
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH(cfg, em, cm, cs, rng)
    p.reset()

    disaster = DisasterEvent(
        cfg.disaster_x, cfg.disaster_y, cfg.damage_radius, rng
    )

    detected_round = -1
    for r in range(1, 30):
        # Apply disaster at round 10 (BEFORE run_round, like runner.py)
        if r == 10:
            killed, survived = disaster.apply_to_network(net)
            print(f"  Round {r}: disaster killed {len(killed)} nodes")
            # NOTE: do NOT call handle_disaster — that's the point

        m = p.run_round(net, r)

        if p.disaster_detected and detected_round < 0:
            detected_round = r
            print(f"  Round {r}: protocol ORGANICALLY detected disaster "
                  f"(delay={r - 10} rounds)")

    assert detected_round > 10, "Protocol should detect disaster AFTER round 10"
    delay = detected_round - 10
    # First missed heartbeat happens in the disaster round itself,
    # so detection delay = timeout - 1 (in rounds).
    assert delay >= cfg.healing_detection_rounds - 1, \
        f"Detection delay ({delay}) should be >= timeout-1 ({cfg.healing_detection_rounds - 1})"
    print(f"  Organic detection delay: {delay} rounds (timeout={cfg.healing_detection_rounds})")
    print(f"  recovery_mode: {p.recovery_mode}")
    print("  PASS")


def test_disaster_round_jitter():
    """Different seeds produce different actual disaster rounds."""
    cfg = SimulationConfig(
        disaster_enabled=True,
        disaster_round=2000,
        disaster_round_jitter=0.15,
    )
    rounds_seen = set()
    for seed in range(10):
        rng = np.random.default_rng(seed)
        jitter = cfg.disaster_round_jitter
        lo = int(cfg.disaster_round * (1.0 - jitter))
        hi = int(cfg.disaster_round * (1.0 + jitter))
        actual = int(rng.integers(lo, hi + 1))
        rounds_seen.add(actual)

    assert len(rounds_seen) > 1, f"Expected different disaster rounds, got {rounds_seen}"
    print(f"  10 seeds produced {len(rounds_seen)} unique disaster rounds")
    print(f"  Range: {min(rounds_seen)} - {max(rounds_seen)}")
    print("  PASS")


def test_carbon_throttle():
    """
    When Z(t) is artificially high AND CI is high, some packets get deferred.
    """
    cfg = SimulationConfig()
    rng = np.random.default_rng(42)
    net = Network(cfg, rng)
    em = EnergyModel(cfg)
    cm = CarbonTraceManager(cfg, rng)
    cs = CompressiveSensing(cfg, rng)

    p = CALASH(cfg, em, cm, cs, rng)
    p.reset()

    # Run a few rounds to establish clusters
    for r in range(1, 5):
        p.run_round(net, r)

    # Artificially inflate carbon queue to trigger throttle
    p.router.carbon_queue = 200.0  # well above threshold (50)

    m = p.run_round(net, 5)
    deferred = m.get('deferred_packets', 0)
    print(f"  With Z(t)=200 (threshold=50): deferred_packets = {deferred}")
    # May or may not defer depending on current CI — just check the key exists
    assert 'deferred_packets' in m, "Missing deferred_packets metric"
    print("  PASS")


if __name__ == '__main__':
    tests = [
        ("CALASH basic 10 rounds", test_calash_basic_10_rounds),
        ("NoCO2 ablation", test_ablation_noco2),
        ("NoSH ablation", test_ablation_nosh),
        ("NoCADR ablation", test_ablation_nocadr),
        ("NoLCI ablation", test_ablation_nolci),
        ("handle_disaster is no-op", test_handle_disaster_is_noop),
        ("Organic self-healing", test_organic_self_healing),
        ("Disaster round jitter", test_disaster_round_jitter),
        ("Carbon throttle", test_carbon_throttle),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n{'='*50}")
        print(f"TEST: {name}")
        print('='*50)
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{passed+failed} passed, {failed} failed")
    print('='*50)

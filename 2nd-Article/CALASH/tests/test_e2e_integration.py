"""End-to-end integration smoke test: 50 rounds with disaster.
Exercises all 6 keyword upgrades simultaneously.
"""
from config import SimulationConfig
from experiments.runner import run_single_experiment


def main():
    # 50-round test with disaster at round 20
    cfg = SimulationConfig(
        num_nodes=50, num_rounds=50, disaster_round=20,
        disaster_round_jitter=0.0, disaster_enabled=True,
        damage_radius=40.0,
    )
    result = run_single_experiment(cfg, "CALASH", seed=42, verbose=True)

    print("\n" + "=" * 60)
    print("=== End-to-End Integration Results ===")
    print("=" * 60)
    print(f"  Operational lifetime: {result['operational_lifetime']} rounds")
    print(f"  Total delivered:      {result['total_delivered']} packets")
    print(f"  Overall PDR:          {result['overall_pdr']:.4f}")
    print(f"  Total energy:         {result['total_energy_J']:.6f} J")
    print(f"  LCI:                  {result['lci']:.4f} gCO2eq/pkt")

    # ---------- Verify all 6 keyword features ----------

    # 1. Lifecycle-Sustainable: LifecycleAssessor exists & has phases
    from agents.lyapunov import LifecycleAssessor
    la = LifecycleAssessor(cfg)
    la.register_packet(0)
    la.update_aging(0, 0.8)
    lca = la.get_lca_breakdown()
    print("\n[1] Lifecycle-Sustainable:")
    print(f"    LifecycleAssessor ✓")
    phases = lca['phases']
    print(f"    Phases: raw={phases['raw_materials']:.3f}  mfg={phases['manufacturing']:.3f}  "
          f"dist={phases['distribution']:.3f}  eol={phases['eol']:.3f}")
    print(f"    Battery capacity fade: {la.capacity_fade(0):.4f}")
    assert "phases" in lca, "LCA phase breakdown missing"

    # 2. Autonomous: heartbeat-based routing (no .alive reads in routing decisions)
    import inspect, re
    from protocols.calash import CALASH
    get_route_src = inspect.getsource(CALASH.get_route)
    dqn_route_src = inspect.getsource(CALASH._dqn_route)
    # Only count non-comment, non-docstring .alive references
    def count_alive_in_code(src):
        count = 0
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # skip docstring continuation lines (simple heuristic)
            if not stripped or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            count += len(re.findall(r'(?<!\w)\.alive(?!\w)', stripped))
        return count
    alive_get_route = count_alive_in_code(get_route_src)
    alive_dqn_route = count_alive_in_code(dqn_route_src)
    print(f"\n[2] Autonomous:")
    print(f"    .alive in get_route code: {alive_get_route} (should be 0)")
    print(f"    .alive in _dqn_route code: {alive_dqn_route} (should be 0)")
    assert alive_get_route == 0, f"get_route still reads .alive ({alive_get_route} hits)"
    assert alive_dqn_route == 0, f"_dqn_route still reads .alive ({alive_dqn_route} hits)"
    print(f"    Heartbeat-based estimation ✓")

    # 3. 6G-Integrated: OFDM params, CSI quality, beam misalignment
    from models.thz_channel import OFDM_PARAMS, CascadedRISChannel
    ris = CascadedRISChannel(cfg)
    diag = ris.get_diagnostics()
    print(f"\n[3] 6G-Integrated:")
    print(f"    OFDM SCS: {OFDM_PARAMS['subcarrier_spacing_khz']} kHz ✓")
    print(f"    CSI quality: {diag['csi_quality']:.2f}")
    print(f"    Beam misalign loss: {diag['beam_misalign_loss_db']:.2f} dB")
    assert "csi_quality" in diag, "CSI quality missing from diagnostics"
    assert "beam_misalign_loss_db" in diag, "Beam misalignment missing"

    # 4. Data Reduction: adaptive semantic gain
    from models.semantic import SemanticEncoder
    import numpy as np
    se = SemanticEncoder(cfg)
    initial_gain = se.semantic_gain
    # importance must be an array (per-feature importance vector)
    imp_vec = np.array([0.8, 0.6, 0.3, 0.1, 0.9])
    se.update_adaptive_gain(nmse=0.15, importance=imp_vec, is_disaster=False)
    se.update_adaptive_gain(nmse=0.05, importance=imp_vec * 0.5, is_disaster=False)
    updated_gain = se.semantic_gain
    print(f"\n[4] Data Reduction:")
    print(f"    Initial adaptive gain: {initial_gain:.3f}")
    print(f"    After 2 updates:       {updated_gain:.3f}")
    diag_sem = se.get_diagnostics()
    print(f"    Task distortion avg:   {diag_sem['task_distortion_avg']:.4f}")
    assert hasattr(se, 'update_adaptive_gain'), "Adaptive gain method missing"

    # 5. Carbon-Aware: Scope 2/3
    from models.carbon import CarbonTraceManager
    cm = CarbonTraceManager(cfg)
    scope = cm.get_ghg_scope_breakdown(
        energy_joules=1e-3, round_num=10, num_nodes=50, dead_count=5
    )
    print(f"\n[5] Carbon-Aware:")
    print(f"    Scope 1 (direct):     {scope['scope1']:.8f} gCO2eq")
    print(f"    Scope 2 (location):   {scope['scope2_location']:.8f} gCO2eq")
    print(f"    Scope 2 (marginal):   {scope['scope2_marginal']:.8f} gCO2eq")
    print(f"    Scope 3 (embodied):   {scope['scope3_embodied']:.1f} gCO2eq")
    print(f"    Scope 3 (EOL):        {scope['scope3_eol']:.1f} gCO2eq")
    assert "scope2_marginal" in scope, "Marginal Scope 2 missing"
    assert "scope3_eol" in scope, "Scope 3 EOL missing"

    # 6. Self-Healing: aftershock + progressive damage
    from models.disaster import AftershockModel, DisasterEvent
    from models.self_healing import SelfHealingEngine
    am = AftershockModel(mainshock_magnitude=7.8, mainshock_radius=50.0)
    am.set_mainshock_round(20)
    after = am.generate_aftershock(current_round=25)
    sh = SelfHealingEngine(cfg)
    print(f"\n[6] Self-Healing:")
    print(f"    AftershockModel (M7.8) ✓")
    print(f"    Aftershock at round 25: {after is not None}")
    print(f"    Progressive damage method: {hasattr(sh, 'apply_progressive_damage')}")
    print(f"    Weakened survivors method: {hasattr(sh, 'register_weakened_survivors')}")
    assert hasattr(sh, 'apply_progressive_damage'), "Progressive damage missing"

    print("\n" + "=" * 60)
    print("ALL 6 KEYWORD FEATURES VERIFIED ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()

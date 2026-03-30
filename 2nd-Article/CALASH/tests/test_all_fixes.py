#!/usr/bin/env python3
"""
Comprehensive smoke test for all code fixes.
Tests: distributed heartbeat, competitive clustering, NoTHz ablation,
       carbon throttle, protocol registry, and end-to-end simulation.
"""

import sys
import os
import inspect
import numpy as np

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import SimulationConfig
from models.network import Network
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.self_healing import HeartbeatTracker, SelfHealingEngine
from protocols.calash import CALASH
from protocols.ablations import (CALASH_NoCO2, CALASH_NoSH,
                                  CALASH_NoCADR, CALASH_NoLCI,
                                  CALASH_NoTHz)
from experiments.runner import PROTOCOL_CLASSES, run_single_experiment

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: {detail}")
        failed += 1


print("=" * 70)
print("  CALASH Comprehensive Fix Verification")
print("=" * 70)

# ── 1. Protocol Registry ─────────────────────────────────────────
print("\n[1] Protocol Registry")
check("13 protocols registered", len(PROTOCOL_CLASSES) == 13,
      f"got {len(PROTOCOL_CLASSES)}: {list(PROTOCOL_CLASSES.keys())}")
check("CALASH-NoTHz in registry", 'CALASH-NoTHz' in PROTOCOL_CLASSES)

# ── 2. HeartbeatTracker distributed mechanism ────────────────────
print("\n[2] HeartbeatTracker (distributed, no .alive flag)")
hb = HeartbeatTracker()
check("has register_heartbeat()", hasattr(hb, 'register_heartbeat'))
check("has _heard_this_round set", hasattr(hb, '_heard_this_round'))

sig = inspect.signature(hb.tick)
params = list(sig.parameters.keys())
check("tick() takes NO network param", 'network' not in params,
      f"params={params}")

# Functional test: simulate heartbeat exchange
cfg = SimulationConfig(num_nodes=10, area_width=100, area_height=100,
                       tx_range=80, healing_detection_rounds=2)
rng = np.random.default_rng(42)
net = Network(cfg, rng)

hb2 = HeartbeatTracker(timeout_rounds=2)
hb2.initialize(net)

# Round 1: all nodes send heartbeats
for node in net.alive_nodes():
    hb2.register_heartbeat(node.id)
detected1 = hb2.tick()
all_empty1 = all(len(s) == 0 for s in detected1.values())
check("All alive → no detections", all_empty1)

# Round 2: kill node 3, it stops sending
net.nodes[3].alive = False
net.nodes[3].energy = 0
for node in net.alive_nodes():
    hb2.register_heartbeat(node.id)
detected2 = hb2.tick()
# After 1 missed round, not yet detected (timeout=2)
node3_detected = any(3 in s for s in detected2.values())
check("1 missed round → not yet detected (timeout=2)", not node3_detected)

# Round 3: node 3 still dead, second miss → detected
for node in net.alive_nodes():
    hb2.register_heartbeat(node.id)
detected3 = hb2.tick()
node3_detected = any(3 in s for s in detected3.values())
check("2 missed rounds → node 3 DETECTED", node3_detected)

# Verify tick never reads .alive (structural check on source)
source = inspect.getsource(HeartbeatTracker.tick)
check("tick() source has NO '.alive' access",
      '.alive' not in source,
      "Still reads .alive flag!")

# ── 3. Competitive Clustering (no LEACH threshold) ──────────────
print("\n[3] Competitive Fitness-Based Clustering")
source_setup = inspect.getsource(CALASH.setup_phase)
check("No 'base_threshold' in setup_phase",
      'base_threshold' not in source_setup,
      "Still uses LEACH threshold!")
check("No 'T_base' in setup_phase",
      'T_base' not in source_setup)
check("'fitness' in setup_phase",
      'fitness' in source_setup,
      "Missing fitness computation!")
check("'is_local_max' in setup_phase",
      'is_local_max' in source_setup,
      "Missing local competition!")

# Functional test: run setup_phase
cfg2 = SimulationConfig(num_nodes=50, area_width=200, area_height=200)
rng2 = np.random.default_rng(123)
net2 = Network(cfg2, rng2)
em2 = EnergyModel(cfg2)
cm2 = CarbonTraceManager(cfg2)

calash = CALASH(cfg2, em2, cm2, rng=rng2)
calash.setup_phase(net2, round_num=1)
chs = net2.cluster_heads()
check(f"setup_phase produces CHs: {len(chs)} CHs from 50 nodes",
      1 <= len(chs) <= 25,
      f"got {len(chs)}")

# ── 4. CALASH-NoTHz ablation ────────────────────────────────────
print("\n[4] CALASH-NoTHz Ablation")
nothz = CALASH_NoTHz(cfg2, em2, cm2, rng=rng2)
check("THz disabled", not nothz._thz_enabled)
check("thz_energy is None", nothz.thz_energy is None)
check("Name correct", nothz.name == "CALASH-NoTHz")

# ── 5. Carbon throttle threshold ────────────────────────────────
print("\n[5] Carbon Throttle Threshold")
cfg_default = SimulationConfig()
check("Threshold lowered to 15.0",
      cfg_default.carbon_throttle_z_threshold == 15.0,
      f"got {cfg_default.carbon_throttle_z_threshold}")

# ── 6. End-to-end simulation (quick, 2 protocols, 100 rounds) ──
print("\n[6] End-to-End Simulation (100 rounds)")
cfg_quick = SimulationConfig(
    num_nodes=30,
    num_rounds=100,
    area_width=150,
    area_height=150,
    disaster_enabled=True,
    disaster_round=40,
    disaster_round_jitter=0.0,
    signal_source='synthetic',
)

for proto_name in ['CALASH', 'CALASH-NoTHz']:
    try:
        result = run_single_experiment(cfg_quick, proto_name, seed=42,
                                       verbose=False)
        alive = result.get('final_alive_nodes', -1)
        pdr = result.get('overall_pdr', -1)
        check(f"{proto_name}: ran OK (alive={alive}, PDR={pdr:.3f})",
              result.get('operational_lifetime', 0) > 0)
    except Exception as e:
        check(f"{proto_name}: ran OK", False, str(e))

# ── 7. All ablations compile and run ────────────────────────────
print("\n[7] All Ablation Variants")
for proto_name in ['CALASH-NoCO2', 'CALASH-NoSH', 'CALASH-NoCADR',
                   'CALASH-NoLCI', 'CALASH-NoTHz']:
    try:
        result = run_single_experiment(cfg_quick, proto_name, seed=42,
                                       verbose=False)
        check(f"{proto_name}: OK (lt={result.get('operational_lifetime', 0)})",
              True)
    except Exception as e:
        check(f"{proto_name}: OK", False, str(e))

# ── Summary ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
total = passed + failed
print(f"  RESULTS: {passed}/{total} passed, {failed}/{total} failed")
print("=" * 70)

if failed > 0:
    sys.exit(1)
else:
    print("\n  🎉 ALL CHECKS PASSED — Code fixes verified!\n")
    sys.exit(0)

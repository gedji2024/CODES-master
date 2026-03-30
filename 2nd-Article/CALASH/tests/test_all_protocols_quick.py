"""Quick end-to-end test: run all 13 protocols for 50 rounds."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from config import SimulationConfig
from models.network import Network
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing
from experiments.runner import PROTOCOL_CLASSES

cfg = SimulationConfig(num_rounds=50)
passed = 0
failed = 0

for name, ProtCls in PROTOCOL_CLASSES.items():
    try:
        rng = np.random.default_rng(42)
        net = Network(cfg, rng)
        em = EnergyModel(cfg)
        cm = CarbonTraceManager(cfg, rng)
        cs = CompressiveSensing(cfg, rng)
        p = ProtCls(cfg, em, cm, cs, rng)
        if hasattr(p, 'reset'):
            p.reset()
        for r in range(1, cfg.num_rounds + 1):
            m = p.run_round(net, r)
        alive = m.get('alive_nodes', '?')
        delivered = m.get('packets_delivered', 0)
        generated = m.get('packets_generated', 1)
        pdr = delivered / max(generated, 1) if generated else 0
        print(f'  OK  {name:<18} alive={alive:>4}  PDR={pdr:.3f}')
        passed += 1
    except Exception as e:
        print(f'  FAIL {name:<18} ERROR: {e}')
        import traceback; traceback.print_exc()
        failed += 1

print(f'\n{passed}/{passed+failed} protocols passed, {failed} failed')
if failed == 0:
    print('ALL PROTOCOLS VERIFIED')

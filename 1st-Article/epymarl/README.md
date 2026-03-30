## EPyMARL (trimmed for RL_Routing project)

This directory contains a pared-down fork of EPyMARL focused on the algorithms actually used in the RL_Routing study (QMIX, QTRAN, QPSOFL baseline integration, and hybrid TSMixer hooks). Upstream documentation is extensive; to reduce duplication we keep only project‑specific notes here. For full features and additional environments see:
https://github.com/uoe-agents/epymarl

### What we use
* Algorithms: QMIX, QTRAN (value factorisation). QPSOFL baseline logic lives under `src/extended_baselines/`.
* Environment: Custom Gym `WSNRouting-v0` (registered via `gym_examples`).
* Feasibility metrics: p95 step time, peak memory, episode time (saved as versioned `.npy` arrays in `results/data/`).

### Running (evaluation example)
```pwsh
# Set algorithm name for metric file suffixing
$env:ALGO_NAME = "QMIX"
python src/main.py --config=qmix --env-config=gymma with env_args.time_limit=30 env_args.key="gym_examples:WSNRouting-v0" evaluate=True test_nepisode=100
Remove-Item Env:ALGO_NAME
```

### QPSOFL
The heuristic + fuzzy baseline is executed via `extended_baselines/qpsofl.py` (no neural network weights; optimisation + rule base). It emits the same metric array schema so the summariser can compare directly.

### Hybrid (TSMixer)
`TSMixer_hybrid_model.py` forecasts next‑step metrics for QMIX/QTRAN and performs a per‑step vote across minimize (latency, energy, std energy) and maximize (returns, throughput, energy efficiency, PDR) groups. The realised metric for the hybrid is the chosen algorithm’s metric.

### Summarising metrics
Use `tools/summarize_npys.py` from repository root:
```pwsh
python tools/summarize_npys.py --budget-ms 10 50 --p95-table --format md --output-file Results_Graphics/feasibility_p95_vs_budgets.md
```

### Citation
If you publish results using QMIX/QTRAN implementations, cite the original PyMARL/SMAC papers (see upstream README). This trimmed file deliberately omits the full citation block; retain it in your manuscript bibliography instead of duplicating here.

### License
Inherited Apache 2.0 license from upstream for original code; new extensions remain Apache 2.0.

Last updated: 2025-11-06

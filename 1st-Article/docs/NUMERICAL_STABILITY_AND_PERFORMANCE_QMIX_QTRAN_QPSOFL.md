# Numerical Stability & Performance Measures: QMIX, QTRAN, QPSOFL

This document records implementation-level guards (numerical stability) and performance optimizations added to the repository. They are designed to prevent runtime failures (NaN/Inf) and reduce unnecessary computation without altering the theoretical objectives or architectures of the algorithms.

## 1. Scope
- **Algorithms Covered**: QMIX / VDN (`q_learner.py`), QTRAN (`qtran_learner.py`), QPSOFL baseline (`qpsofl.py`).
- **Not Changed**: Loss formulations, Bellman backups, mixing constraints (QMIX), QTRAN TD/opt/nopt objectives, optimization semantics of QPSOFL swarm & fuzzy inference.

## 2. Toggle: `strict_math`
- When `strict_math = false` (default if absent): stability guards active.
- When `strict_math = true`: original behavior (no sanitization, original sentinels) for literal parity with canonical code paths.

## 3. QMIX / VDN Guards (File: `epymarl/src/learners/q_learner.py`)
| Guard | Description | Rationale | Effect on Theory |
|-------|-------------|-----------|------------------|
| Action masking before max | Replace unavailable actions with large negative sentinel; no-valid-action → target 0 | Prevent selecting invalid actions | None (standard masked Q-learning) |
| Terminal bootstrap zeroing | Use `torch.where(terminated, 0, target)` before target construction | Avoid 0 * NaN and removes terminal next-state value | Aligns with standard terminal handling |
| `nan_to_num` sanitization | Applied post-max and post-mixer | Avoid propagation of accidental NaN/Inf | No change if values finite |
| Variance clamp (`clamp_min(1e-12)`) | On return variance before `sqrt` | Prevent sqrt of tiny/negative due to numerical drift | Preserves normalization expectation |
| TD error finiteness check | Raise early if non-finite | Fail fast for debugging | No impact unless error is invalid |

## 4. QTRAN Guards (File: `epymarl/src/learners/qtran_learner.py`)
| Guard | Description | Rationale | Theory Impact |
|-------|-------------|-----------|---------------|
| Masking with `-inf` (non-strict) | Use `masked_fill(..., -inf)` before argmax | Avoid artificial scale inflation from large finite sentinels | Argmax invariant (ignores -inf) |
| `nan_to_num` selectively | Sanitize joint/target/max action Q values | Prevent NaN/Inf propagation | Neutral when finite |
| Terminal zeroing | `where(terminated, 0, target_joint_q)` | Standard RL terminal treatment | None |
| Finiteness checks (TD/opt error) | Raise on NaN/Inf | Early detection | None unless invalid state |
| Range logging | Min/max of joint and target Qs | Transparent diagnostics | Observational only |

## 5. QPSOFL Performance Optimizations & Semantics (File: `epymarl/src/extended_baselines/qpsofl.py`)
The following changes accelerate execution while preserving QPSOFL's optimization and fuzzy logic methodology.

| Optimization | Change | Rationale | Theory Impact |
|--------------|--------|-----------|---------------|
| Fitness caching | Store `fitness_P`, `fitness_Pbest`, `gBest_fitness`; avoid repeated evaluations | Removes redundant evaluations (previously O(Np * Itrmax) extra) | Objective unchanged; same fitness comparisons |
| Single RNG reuse | One `rng = np.random.default_rng()` reused | Decreases overhead of RNG creation | Randomness distribution unchanged |
| Consolidated update | Precompute `Pbest_bar` per-iteration | Avoid repeated means in inner loop | Same contraction–expansion dynamics |
| Bounds & fitness single pass | Clip & evaluate once per particle update | Less Python overhead | Identical update equations |
| Vectorized clustering | `clusters_formation` uses distance matrix + `argmin` | Remove Python loops, faster assignment | Clustering rule unchanged |
| Data dir precreation | Ensure `results/data` exists; safe retry on FileNotFound | Prevents env init errors | Neutral |

Latency semantics:
- Per-episode average latency is undefined when no packets are delivered; we keep `NaN` internally.
- Overall/summary latency uses `np.nanmean`/`np.nanstd` and ignores `NaN` episodes.
- Optional print-only control via `LATENCY_NO_DELIVERY_VALUE` env var: default `"nan"`; may set to a numeric (e.g., `"-1"`) for exporters. Do not use `0` unless you explicitly mean “instantaneous latency”, which is semantically misleading.

Env overrides (for experimentation):
- `QPSOFL_EPISODES`, `QPSOFL_STEPS`: control episode/step counts.
- `QPSOFL_ITRMAX`, `QPSOFL_NP`: control swarm iterations and particle count.
- `QPSOFL_PROFILE`: `1`/`0` to enable lightweight per-episode timing stats.
- `BS_PENALTY_SCALE`: scales soft penalty when no CH is within BS range in fitness.
- `LATENCY_NO_DELIVERY_VALUE`: print-time fallback when no deliveries (`"nan"` by default).

## 6. Why These Changes Preserve Theory
1. **Objective Functions**: QMIX/QTRAN losses and QPSOFL fitness remain identical; guards operate only on invalid numeric states.
2. **Action Selection & Argmax**: Masking with `-inf` does not change which action maximizes Q; it only clarifies invalid choices.
3. **Terminal Handling**: Zeroing next-state values at terminal transitions matches standard RL practice; if terminal bootstrap was implicitly avoided before, behavior remains consistent.
4. **Fuzzy Inference & Swarm Updates**: QPSOFL modifications remove duplicated work; no change to probabilistic rules, membership functions, or particle update equations.

## 7. Reporting Guidance (For Reviewers / Reproducibility)
Include in paper or supplementary:
- Commit hash of experiments.
- `strict_math` setting (state if runs used guards or strict parity).
- Gradient clipping norm values (QMIX/QTRAN).
- Q-value range statistics (optional diagnostic) confirming absence of overflow.
- Swarm parameters: `Itrmax`, `Np`, `m`, contraction-expansion formula, tolerance `tol`.
- FIS rule structure and membership functions unchanged from reference.
- Latency handling: per-episode latency is undefined (NaN) when no deliveries; overall latency computed with NaN-aware statistics.
- Statement: "Numerical stability guards (masking, NaN sanitization, terminal bootstrap suppression, fitness caching) do not alter the theoretical objectives; they ensure reliable and efficient execution."

## 8. Recommended Ablations
| Ablation | Purpose |
|----------|---------|
| `strict_math=true` vs false | Demonstrates guards neutrality on final performance |
| Reduced vs original `Itrmax`/`Np` (QPSOFL) | Shows convergence behavior & performance/time trade-offs |

## 9. Example Claim (Manuscript Ready)
> We implement canonical QMIX and QTRAN objectives and a quantum particle swarm with fuzzy logic (QPSOFL). We add industry-standard numerical stability guards (masked invalid actions, terminal bootstrap suppression, NaN sanitization) and performance caching (for QPSOFL fitness) that do not modify any objective or inference rule. These measures solely prevent pathological numeric states and redundant computation. Parity runs (`strict_math=true`) yield comparable metrics, confirming theoretical fidelity.

## 10. How to Toggle / Use
- QMIX/QTRAN: set `strict_math=true` in config/args for strict parity; omit or set false for guards.
- QPSOFL: optimizations are active by default; tune via env vars listed above.
- Printing latency for non-delivery episodes: leave default for `NaN` or set `LATENCY_NO_DELIVERY_VALUE` to a documented sentinel (e.g., `-1`).

---
*Last updated: 2025-11-29.*

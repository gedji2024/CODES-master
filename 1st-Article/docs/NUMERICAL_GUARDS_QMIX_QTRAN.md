# Numerical Stability Guards for QMIX and QTRAN

This repository includes targeted numerical stability guards for QMIX and QTRAN. These safeguards prevent NaN/Inf propagation and edge-case crashes without changing the underlying learning objectives or architectures.

- Affected files:
  - `epymarl/src/learners/q_learner.py` (QMIX/VDN)
  - `epymarl/src/learners/qtran_learner.py` (QTRAN)
- Toggle (default off for strict mode):
  - Runtime arg: `strict_math` (default: false → guards ON). When `strict_math=true`, the code follows the original behavior (guards OFF) for literal parity.

## What Was Added

### Common Principles
- Masking is applied before argmax/`max` so invalid actions cannot be selected.
- Terminal transitions zero next-state bootstrap values to avoid 0×NaN issues.
- Non-finite sanitization (`nan_to_num`) prevents accidental NaN/Inf from halting training.
- Defensive checks raise with a clear message when a non-finite value appears (disabled in strict mode).

### QMIX (`q_learner.py`)
- Unavailable actions are masked prior to max/gather. If an agent has no valid action at the next step, its target is set to 0.
- Next-state bootstrap for terminal steps is explicitly zeroed using `torch.where` to avoid numeric edge cases.
- `torch.nan_to_num` is applied after max/gather and after mixing to sanitize values if upstream code produced non-finite numbers.
- Return variance is clamped with `clamp_min(1e-12)` before square root in de-standardization to prevent negative/near-zero variance artifacts.
- An early finiteness assertion on TD error fails fast instead of silently propagating NaNs (disabled in strict mode).

### QTRAN (`qtran_learner.py`)
- Non-finite sanitization is applied to `max_actions_qvals`, mixer outputs, and intermediate values.
- Terminal targets are zeroed via `torch.where` to avoid bootstrap on terminal transitions.
- Early finiteness checks for TD/opt errors are added to fail fast (disabled in strict mode).
- Note: We intentionally do not clamp or rescale large but finite Q-values—this preserves the objective while improving robustness.

## Why This Does Not Change the Theory
- The Bellman targets, mixer architectures, and loss definitions (QMIX: monotonic mixing with 1-step Q-learning; QTRAN: TD, opt, nopt objectives) are unchanged.
- The guards enforce the standard assumptions in value-based RL practice:
  - Mask invalid actions before action selection.
  - Do not bootstrap at terminal transitions.
  - Prevent NaN/Inf from upstream numeric issues (e.g., divisions by zero or degenerate statistics) from entering the loss.
- These measures are common in robust RL implementations and do not alter the policy class, objective, or constraints introduced by QMIX or QTRAN.

## Reproducibility and Reporting Guidance
- Report the `strict_math` setting:
  - `strict_math=false` (default): guards ON for robustness; canonical objectives preserved.
  - `strict_math=true`: guards OFF for literal parity to classic code paths.
- Always include: algorithm (QMIX/QTRAN), optimizer, learning rate, gradient clipping norm, reward scaling, gamma, batch size, random seeds, and commit hash.
- Recommend an ablation: run a subset with `strict_math=true` to show results are consistent (the guards only prevent NaN/Inf, not change objectives).
- If your environment can yield no-valid-action timesteps, state that such states have target 0 by definition (no action to select), which is consistent with standard masked Q-learning semantics.

## Practical Notes for QTRAN and Large Magnitudes
- Large (finite) gradient norms can occur early due to the structure of the QTRAN losses (joint Q + V, opt/nopt terms) and reward scales.
- To keep magnitudes reasonable without changing the objective:
  - Use gradient clipping (e.g., global-norm clip of 10–20).
  - Prefer masking via `masked_fill(..., -inf)` before `max`, then sanitize after `max` only if needed.
  - Ensure reward scaling is sensible for your domain.
  - Log ranges of `joint_qs`, `target_joint_qs`, and gradient norms for diagnostics.

## How to Toggle
- Via args/config (example): set `strict_math: true` to disable all guards for literal parity runs; omit or set `false` to keep guards enabled by default.

## Summary Claim
These stability guards are implementation-level safety practices that do not alter the QMIX or QTRAN objectives or their theoretical constraints. They ensure training proceeds reliably in the presence of edge cases and numeric noise while preserving methodological fidelity.

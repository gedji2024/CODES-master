# CASTER-ZT: Complete Deep Explainer for a First-Year Software Engineering Student

> **Who is this for?** You are a first-year SE student. You may have taken one course in programming and perhaps a basic algorithms course. You have never read the paper. By the end of this document you should be able to explain every idea in CASTER-ZT to another student — not just memorize facts, but truly understand *why* each piece exists.
>
> **How this document is organized:** Seven pedagogical steps, always building on the previous one. If something feels unclear, go back one step — the vocabulary or context you need is probably there.
>
> **A promise about honesty:** This document will never claim something without telling you exactly where the evidence comes from. When something is uncertain, assumed, or limited, we say so plainly.
>
> **Estimated reading time:** ~3–4 hours for the full document. Steps 1–2 + the Cheat Sheets alone take ~45 minutes and give you a working vocabulary and big picture. Return to Steps 3–7 and the Appendices once you have that foundation.

---

## Table of Contents

- [Step 1 — Vocabulary and Terminology](#step-1-vocabulary-and-terminology)
- [Step 2 — Context and Motivation](#step-2-context-and-motivation)
- [Step 3 — Literature Review](#step-3-literature-review)
- [Step 4 — Methodology: How CASTER-ZT Works](#step-4-methodology-how-caster-zt-works)
- [Step 5 — Results: Every Number Explained](#step-5-results-every-number-explained)
- [Step 6 — Discussion and Limitations](#step-6-discussion-and-limitations)
- [Step 7 — Conclusion](#step-7-conclusion)
- [Appendix A — The Ten Propositions Deep-Dive](#appendix-a-the-ten-propositions-deep-dive)
- [Appendix B — Expert Q&A](#appendix-b-expert-qa)
- [Appendix C — Quick-Reference Cheat Sheets](#appendix-c-quick-reference-cheat-sheets)

---

<a id="step-1-vocabulary-and-terminology"></a>
## STEP 1 — Vocabulary and Terminology

*Before anything else: words. You cannot understand the paper without understanding its vocabulary. Read every definition carefully. Return to this section whenever you encounter an unfamiliar term.*

---

### 1.1 The World of 6G and Mobile Networks

**Cellular network:** A network of radio towers ("cells") that together cover a geographic area and provide wireless communication. Your phone connects to the nearest cell, which routes your data to the internet. A "cell" is both the tower and its coverage area.

**6G:** The 6th generation of mobile wireless standards. Not yet deployed (as of 2025). Expected features: latency < 1 ms, throughput > 1 Tbps, deep AI integration ("AI-native"), massive edge computing. Think of it as 5G but 10× faster with built-in intelligence.

**O-RAN (Open Radio Access Network):** An industry initiative to "open up" the hardware and software of cellular base stations so that components from different vendors can interoperate. Traditionally a single vendor (Nokia, Ericsson) supplied the entire base station as a closed black box. O-RAN breaks it into standardized open interfaces.

**Near-RT RIC (Near-Real-Time RAN Intelligent Controller):** An O-RAN component that makes decisions on a 10 ms to 1 second timescale. CASTER-ZT's shield must decide within this 10 ms window. *Evidence: O-RAN nGRG (2024) formally specifies the Near-RT RIC timescales.*

**xApp:** A small software application deployed inside the Near-RT RIC. CASTER-ZT is conceptually deployed as an xApp.

**Telemetry:** Measurements automatically collected and transmitted from remote equipment. In a cellular network: throughput (how fast data flows), latency (how long a packet takes), packet loss rate (fraction of packets dropped), cell load (how busy a cell is). Think of it as the "vital signs" of the network.

**Zone:** A logical grouping of cells managed together. A 12-cell network has 2 zones; a 100-cell network has 8 zones.

---

### 1.2 The Disaster Scenario

**Disaster-monitoring sensing network:** A wireless network deployed in a disaster area (earthquake, flood, hurricane) to gather environmental sensor data and coordinate emergency response. In a disaster, many cell towers may fail simultaneously.

**Simultaneous failure fraction:** In the experiments, 40% of cells fail at the same time (tick 3 of each episode). This is calibrated from SensorScope alpine deployment data: during storm events, sensor dropout peaked at approximately 40% simultaneously. *Evidence: SensorScope dataset (2008), cited in the paper.*

**Recovery action:** A command sent by the AI controller to restore service. Six types are defined: CELL_RECONFIG, LOAD_REBALANCE, POWER_BOOST, HANDOVER, CELL_ISOLATION, CELL_DEACTIVATION.

**Rogue action:** A recovery-type action injected by an adversary that appears legitimate but is designed to cause harm (e.g., CELL_DEACTIVATION targeting a healthy cell).

**Episode:** One complete simulation run lasting 30 "ticks." One tick represents one decision cycle of ~10 ms.

**omega_rec (Recovery Quality):** The primary performance metric. The mean fraction of cells in the OPERATIONAL state during ticks [3, 33]. Value of 1.0 = all cells operational throughout recovery. Value of 0.0 = no cells ever recover. *Evidence: defined in Section III-B of the paper.*

---

### 1.3 Security Concepts

**Zero Trust:** A security philosophy where no entity is implicitly trusted, ever. Every request, even from inside the system, must be continuously verified. Defined in NIST Special Publication 800-207.

**Identity-credential abuse:** An attack where the adversary steals valid credentials from a legitimate operator and uses them to issue rogue commands. Because the credentials are real, standard authentication passes.

**Telemetry poisoning:** An attack where the adversary manipulates the telemetry data sent by sensors (e.g., injecting false measurements).

**Combined attack:** Both identity-credential abuse AND telemetry poisoning simultaneously. The hardest attack type.

**Rogue detection rate (RogueDet):** Fraction of adversary-injected rogue actions that the system correctly identifies and reacts to (blocks or scope-reduces). In the experiments: 0.742 at 12-cell = 74.2% detection.

**False block rate (FalseBlk):** Fraction of hard BLOCK decisions applied to legitimate (non-rogue) actions. FalseBlk = 0.000 in CASTER-ZT means the system never wrongly issues a hard BLOCK on a legitimate action.

> ⚠️ **Important nuance:** FalseBlk only counts hard BLOCK outcomes. Under clean (no-attack) conditions, CASTER-ZT scope-reduces ~10% of legitimate actions. SCOPE-REDUCE is a softer intervention (execute with fewer target cells) but it does constrain legitimate behavior. Zero hard false-blocks does NOT mean zero impact on legitimate operations. See Section 5.8 for the full clean-condition breakdown.

**Precision vs. Recall (for security classification):**

Imagine you are a doctor doing cancer screening. You can choose:
- **High recall:** Test positive for any suspicious sign — catch 100% of real cases, but also alarm many healthy patients.
- **High precision:** Only declare cancer when you are very sure — very few false alarms, but may miss some real cases.

Applied here:
- **Recall (= RogueDet):** Fraction of rogues caught. 74.2% = CASTER-ZT catches 74.2 out of every 100 rogues.
- **Precision (= 1 - FalseBlk):** Fraction of blocked actions that are truly rogue. 100% precision = every block/constraint the shield imposes is on a genuinely suspicious action.

CASTER-ZT deliberately chooses maximum precision (zero false hard-blocks) at the cost of imperfect recall (74.2%). The paper argues this is correct: falsely blocking a legitimate recovery action during a disaster directly delays restoring service and could cost lives.

**Mimicry attack:** A sophisticated attack where rogue actions are designed to look as much as possible like legitimate recovery actions (e.g., a rogue CELL_RECONFIG targeting a nearly-failed cell — hard to distinguish from a legitimate one). These are the hardest to detect.

**Gray-box adversary:** The paper's threat model assumes the adversary knows the system's architecture but NOT the exact threshold values of the shield. *Evidence: Section III-B of the paper.*

---

### 1.4 Machine Learning Concepts

**ReLU (Rectified Linear Unit):** The most common activation function in neural networks. Formula: `ReLU(x) = max(0, x)`. In plain English: if the input is negative, output 0; if positive, output it unchanged. This introduces non-linearity (without which a stack of linear layers collapses to just one linear layer).

**Softmax:** A function that converts a vector of raw scores into a probability distribution summing to 1. Example: raw scores [2.0, 1.0, 0.1] → softmax → [0.66, 0.24, 0.10]. Used in the policy head to output "probability of each action type."

**One-hot encoding:** A way to represent a category as a vector of zeros with a single 1. Example: 6 action types, POWER_BOOST is type 3 → one-hot vector = [0, 0, 1, 0, 0, 0]. This lets neural networks process categorical inputs as numbers.

**Graph Neural Network (GNN):** A type of neural network designed to process graph-structured data. A graph has nodes (cells) connected by edges (communication links). A GNN propagates information along edges: each node aggregates information from its neighbors. After L layers of propagation, each node's representation captures context from its L-hop neighborhood.

```
Before GNN:                  After GNN (L=2 layers):
Cell A knows only itself.    Cell A "knows about" its neighbors
                              and its neighbors' neighbors.
      [B]                           [B]
      / \                           / \
    [A]--[C]   →   A's embedding contains info from B, C, and D
      \                             \
      [D]                           [D]
```

**Embedding:** A fixed-size vector representation of something complex. The GNN produces a 64-dimensional vector (embedding) for each cell, encoding its state, its neighbors' states, and the network context. Think of it as a 64-number "summary" of what is happening around that cell.

**Autoencoder (AE):** A neural network trained to reconstruct its input. It first compresses the input to a small "bottleneck" representation, then expands it back to the original size. When trained ONLY on clean (normal) data, it learns what "normal" looks like and reconstructs normal inputs well. For unusual inputs, it cannot reconstruct well — the reconstruction error is high.

```
Autoencoder structure:

Input (7 numbers)
    ↓  [Compress]
  32 numbers (ReLU)
    ↓
  16 numbers (ReLU)
    ↓
   8 numbers  ← BOTTLENECK (most compressed)
    ↓
  16 numbers (ReLU)
    ↓
  32 numbers (ReLU)
    ↓  [Expand]
Output (7 numbers, should match input)

Reconstruction error = ||Input - Output||
                     = how different the input and output are
```

**Reconstruction error:** Formally: `e = ||x - AE(x)||_2` (Euclidean distance between input and reconstructed output). A small e means "normal input, the AE recognized it." A large e means "unusual input, the AE struggled."

**Contrastive learning:** A training approach where a model is shown pairs of examples and learns:
- *Similar* pairs → produce *close* representations in embedding space
- *Dissimilar* pairs → produce *far* representations in embedding space

*Analogy:* Imagine a face recognition system. You show it photos of the same person (similar pair) and photos of different people (dissimilar pair). It learns to place the same person close together and different people far apart in a "face space." CASTER-ZT uses this for clean vs. adversarial telemetry.

**MC-Dropout (Monte Carlo Dropout):** A technique for estimating how uncertain a neural network is about its prediction. Normally during inference, dropout is turned off. MC-Dropout keeps it ON and runs many forward passes. Each pass randomly disables different neurons, producing a slightly different output. The *variance* across many passes tells you how uncertain the model is.

*Analogy:* Ask 20 doctors to give a diagnosis, but each one is blindfolded to a random subset of the patient's test results. If all 20 agree → high confidence. If they give different answers → high uncertainty.

**The Bayesian argument behind MC-Dropout:** Gal and Ghahramani (ICML 2016) mathematically proved that a neural network with dropout, run many times with different random masks, is equivalent to sampling from a probability distribution over possible models (called a "Bayesian posterior" — literally, your best estimate of which model parameters are correct, updated after seeing data). The variance across passes therefore represents genuine probabilistic uncertainty, not just random noise. *Evidence: Gal and Ghahramani, ICML 2016 — "Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning."*

**Imitation learning:** Training a policy to copy the actions of a human expert, rather than learning by trial and error (which is Reinforcement Learning).

*Analogy:* Learning to drive by watching an experienced driver (imitation learning) versus learning by getting in a car alone and being rewarded when you don't crash (reinforcement learning). Imitation is much safer and faster when expert demonstrations exist.

**Conformal prediction:** A mathematical framework for making predictions with guaranteed error rates, without assuming anything about the data distribution. The only requirement is *exchangeability*.

**Exchangeability:** A sequence of data points is exchangeable if you could shuffle their order and the statistical behavior would be unchanged — i.e., no time-trend or ordering effect matters.

*Analogy:* A bag of marbles. If you draw 10 marbles in any order, the statistics of what you draw don't depend on the order. This is exchangeability. A time series where tomorrow depends on today is NOT exchangeable.

**K-S test (Kolmogorov-Smirnov test):** A statistical test that checks whether a data sample matches a specified distribution. The *p-value* is the probability that you would observe data *at least as different as you observed*, if the data truly came from that distribution.

- p-value close to 0 → the data looks very different from the specified distribution (reject it).
- p-value close to 1 → the data looks perfectly consistent with the distribution (no reason to reject).

Scientists conventionally use p > 0.05 as "acceptable." A p > 0.68 means: "Even if the distributions were a perfect match, you'd see data this different 68% of the time — there is very strong agreement." *Evidence: K-S test p > 0.68 reported in the paper's Section III-C.*

---

### 1.5 Decision and Control Concepts

**Shield:** A safety component that wraps a controller and intercepts its output actions, overriding any action that violates a safety specification. The controller proposes; the shield decides whether to allow, modify, defer, escalate, or block.

**Deterministic:** A system that, given the same input, always produces the same output. CASTER-ZT's shield is deterministic: identical values of (tau, rho, u, Delta, alpha) always produce the same decision. This is deliberately chosen — see Section 4.8 for why.

**Five outcomes (Decision Space D):**

| Symbol | Name | Meaning |
|--------|------|---------|
| ALLOW | Allow | Execute the action as proposed |
| SCOPE-REDUCE | Scope Reduction | Execute a narrowed version (fewer target cells, lower intensity) |
| DEFER | Defer | Do not execute now; wait for more information |
| ESCALATE | Escalate | Send to a human operator for judgment |
| BLOCK | Block | Reject the action entirely |

**Composite conservatism score (g_t):** A single number that aggregates all threat signals into one measure of "how cautious should the shield be." Higher g_t = more conservative shield response.

Formula: `g_t = 0.25*(1-tau) + 0.25*rho + 0.25*u + 0.25*Delta`

- (1-tau): distrust in telemetry (high if telemetry looks manipulated)
- rho: risk of the proposed action
- u: uncertainty of the AI model
- Delta: divergence between benign and adversarial interpretations

Each component is in [0,1]. Delta can theoretically exceed 1.0 (it is unbounded above). Therefore **g_t can exceed 1.0**. This is not a bug — Rule 7 in the shield (`g >= 0.90 → BLOCK`) catches all high-g_t cases, including those above 1.0.

**Dynamic trust minimum (tau_min):** The minimum trust score required for the shield to output ALLOW. It *rises* when risk or uncertainty is high.

Formula: `tau_min = 0.50 + 0.10*rho + 0.15*u`

*Intuition:* When the AI is uncertain (high u) or the action is dangerous (high rho), the system demands MORE trust evidence before allowing. If you're about to deactivate 5 cells (high rho), you need very clean telemetry to get the green light.

---

### 1.6 Mathematical Notation Summary

| Symbol | What it is | Range | Meaning |
|--------|-----------|-------|---------|
| tau_t | Trust score | [0,1] | How much the system trusts the current telemetry |
| rho_t | Risk score | [0,1] | How risky the proposed action is |
| u_t | Uncertainty | [0,1] | How uncertain the AI model is |
| Delta_t | Divergence | [0, +∞) | How different benign vs adversarial interpretations are |
| alpha_t | Authorization | {0,1} | 1 = authorized entity, 0 = unauthorized |
| g_t | Conservatism score | [0, +∞) | Aggregated threat signal (CAN exceed 1.0) |
| tau_min | Minimum trust required | [0.5, 0.65] | Adaptive trust demand |
| d_t | Decision | D | Output of the shield |
| omega_rec | Recovery quality | [0,1] | Mean fraction of operational cells during recovery window |
| gamma_1..4 | Shield thresholds | [0,1] | 0.30, 0.50, 0.70, 0.90 |
| delta_max | Soft divergence limit | 0.50 | Divergence beyond which ALLOW is blocked |
| delta_max_hard | Hard divergence limit | 1.00 | Divergence beyond which only BLOCK is possible |
| epsilon_alpha | Auth false-neg rate | [0,1] | Probability auth gate misses an attack |
| epsilon_tau | Trust false-neg rate | [0,1] | Probability trust-risk gate misses an attack |
| L | GNN layers | 2 | Number of message-passing rounds |
| d | Latent dimension | 64 | Size of each cell embedding vector |
| T | MC-Dropout passes | 20 | Number of stochastic forward passes |
| eta_AI | AI-native coverage | [0,1] | Fraction of 6G-AISF requirements met |

---

<a id="step-2-context-and-motivation"></a>
## STEP 2 — Context and Motivation

*Why does this problem exist? Why does it matter? Why is it hard?*

---

### 2.1 The Scenario: A Disaster Strikes

Imagine a Category 4 hurricane hits a coastal city. Within 30 minutes:
- 40% of cellular towers are destroyed or lose power.
- First responders need to communicate.
- Hospitals need to coordinate patient transfers.
- Smart city systems need status updates.

The cellular network is the lifeline. Every minute of degraded communication could cost lives.

Now imagine the network has an AI controller — a small program running *close to the disaster zone* (at the network "edge," not in a distant data center) — that automatically decides how to reconfigure the surviving towers. This is CASTER-ZT's setting.

### 2.2 Why Autonomous Recovery Is Needed

**Problem 1: Speed.** Human network operators can reconfigure maybe 5–10 cells per hour manually. An AI can reconfigure thousands in seconds.

**Problem 2: Backbone disconnection.** If the disaster destroys the fiber links to the main internet backbone, human operators in remote data centers may be unreachable. The AI must operate autonomously at the edge.

**Problem 3: Scale.** A real cellular network has hundreds to thousands of cells. No human team can watch all of them simultaneously every 10 milliseconds.

**The O-RAN timescale constraint:** The Near-RT RIC operates on 10 ms to 1 second timescales. Any decision algorithm must complete in under 10 ms. This is why CASTER-ZT is so small (~20K parameters, ~80 KB). *Evidence: O-RAN nGRG (2024).*

### 2.3 Why Autonomous Recovery Is Dangerous

An AI that controls the network has enormous power: it can deactivate cells, reroute thousands of connections, isolate zones. What happens if a malicious actor tricks it?

**Attack vector 1: Stolen credentials.** An adversary gains a compromised operator account. Any AI that trusts "authorized identity = safe" will execute whatever this adversary sends.

**Attack vector 2: Sensor manipulation.** The adversary injects false telemetry. The AI "sees" a problem that does not exist, or fails to see a real problem.

**Real-world grounding:** These attack patterns are grounded in the SWaT (Secure Water Treatment) and WADI industrial control system testbeds. *Evidence: Goh et al., SWaT (2017); WADI dataset (2018) — public testbeds from Singapore University of Technology and Design.* Both testbeds documented cases where sensors were manipulated to inject false readings into automated control systems.

### 2.4 The Key Insight Behind CASTER-ZT

The paper's central observation: **no single existing method simultaneously achieves all three of:**
1. Rogue action detection (catch the bad guys)
2. Enforcement precision (never wrongly constrain good actions)
3. Clean-condition operational transparency (don't slow down the system when there is no attack)

See Section 3.5 for the evidence for this claim across four prior methods.

### 2.5 The Regulatory Context

**EU AI Act (2024):** Classifies AI in critical infrastructure as "high-risk." Requires: auditable decisions, risk management processes, human oversight mechanisms.

**NIST AI Risk Management Framework (2023):** Requires structured risk assessment, continuous monitoring, and human-in-the-loop fallback.

CASTER-ZT's deterministic shield (auditable), formal proofs (risk management), and defer/escalate pathways (human oversight) directly address these requirements.

---

<a id="step-3-literature-review"></a>
## STEP 3 — Literature Review

*What has been done before? What does each prior work do, how does it work, and why is it not sufficient?*

---

**Why study prior work?** In science, no paper starts from zero. You must show (1) what approaches already exist, (2) what each approach can and cannot do, and (3) where the gap is that your new method fills. Without this, a reader cannot judge whether the problem was truly unsolved. This section is the scientific justification for CASTER-ZT's existence.

---

### 3.1 CPO-Soft — Constrained Policy Optimization

**Reference:** Achiam et al., "Constrained Policy Optimization," ICML 2017.

**Tech stack:** Reinforcement learning with cost constraints. To understand the adaptation: a "Lagrangian" is a mathematical trick for handling constraints — it adds a penalty term (the "Lagrange multiplier × violation") to the objective function, so violating a constraint becomes expensive to the optimizer. Plain English: "train the AI to maximize recovery while adding a cost penalty for expensive actions."

**Methodology:** CPO learns a policy that maximizes expected reward while keeping cumulative cost below a budget. Cost function in CASTER-ZT's adaptation: `c(a, s) = rho * |scope(a)|` (risk × number of target cells). Budget = 75th percentile of clean costs. If cumulative cost exceeds budget: block. Otherwise: allow.

**Why it fails:** Rogue actions are NOT expensive — they are *unauthorized*. A rogue CELL_DEACTIVATION targeting one cell has the same cost as a legitimate one. CPO has no concept of identity. It cannot detect "this action is from a stolen credential."

**Result in experiments:** 0% rogue detection. omega_rec = 0.201 (catastrophic, same as no shielding). *Evidence: Table III in the paper.*

**Structural limitation:** Cost-constraint approaches distinguish *how expensive* an action is, not *who* is requesting it or *whether the telemetry is honest*.

---

### 3.2 Shield-Binary — Formal Safety Shield

**Reference:** Alshiekh et al., "Safe Reinforcement Learning via Shielding," AAAI 2018.

**Tech stack:** Formal methods. Precomputed binary safety automaton. A "safety automaton" is a finite-state machine that reads the sequence of (state, action) pairs and outputs allowed/blocked.

**Methodology:** A safety specification is written as invariants (rules that must never be violated). Every (state, action) pair is pre-labeled safe (allow) or unsafe (block). Binary only — no middle ground.

Three invariants in CASTER-ZT's adaptation:
1. Action-rate limit: ≤ 2 recovery actions per zone per 3-tick window.
2. Blast-radius bound: ≤ 3 cells per action.
3. Zone-safety invariant: no isolation where > 60% of cells are already failed.

**Why it partially works:** The rate limit catches some rogues (adversaries injecting many actions quickly). But it also catches legitimate recovery surges during peak failure periods.

**Result:** RogueDet = 88.3%, FalseBlk = 48.8%, omega_rec = 0.758. Nearly half of all block decisions are wrong — they block legitimate recovery actions. *Evidence: Table III in the paper.*

**Structural limitation:** Binary shields have only two outputs: allow or block. When uncertain, they must block. This is called the "price of conservatism."

---

### 3.3 Agentic-Auto — Confidence-Based Autonomous Controller

**Reference:** Navidan et al. (2026), "Toward Autonomous O-RAN with Agentic Intelligence."

> ⚠️ **Transparency note:** This reference is marked as "approximate" in the paper — the cited work was in-press at time of writing. Results for this baseline should be interpreted with that caveat.

**Tech stack:** Confidence thresholding on a neural policy.

**Methodology:** `Confidence = pi(a|s) / max_{a'} pi(a'|s)` (ratio of the top-1 action probability to the maximum possible). If confidence ≥ 0.72: execute. If < 0.72: defer.

*Intuition:* If the model is very sure which action to take, execute it. If unsure, wait for more information.

**Why it fails:** Confidence measures *prediction quality*, not identity legitimacy or action safety. Rogue actions of common types (like CELL_RECONFIG, which appears often in training) produce high confidence — the model "knows" the action type, even though the requester is malicious.

**Result:** RogueDet = 10.5%, FalseBlk = 56.8%. Worst external baseline. *Evidence: Table III in the paper.*

---

### 3.4 IF-Trust — Isolation Forest Trust Assessment

**Reference:** Zahoor et al. (2025), approximate reference zahoor2025ifocsvm.

> ⚠️ **Transparency note:** This is an internal ablation baseline, not an externally published system. Its purpose is to isolate the contribution of the neural autoencoder vs. a classical anomaly detector.

**Tech stack:** Classical ML. Isolation Forest (100 trees, 5% contamination) replaces the neural autoencoder.

**How Isolation Forest works:** Randomly partitions data into trees. Points that are easy to isolate (few splits needed) are anomalies. Points that require many splits are normal.

**Why it fails in disasters:** In a disaster, telemetry is *already* abnormal (cells failing, loads shifting, latencies spiking). From the Isolation Forest's perspective, everything looks anomalous — it has no model of "this is what normal disaster-recovery telemetry looks like." It scope-reduces virtually everything.

**No contrastive encoder:** Because the Isolation Forest provides no reconstruction residual (unlike the autoencoder, which outputs `delta_hat = x - AE(x)`), Delta_t = 0 for this baseline. The divergence channel is completely absent.

**Under attack:** RogueDet = 100%, omega_rec = 0.925 (catches all rogues by throttling all actions).
**Under no attack:** 100% scope-reduction — pathological behavior, makes autonomous operation pointless.

**Why methodologically revealing:** IF-Trust and full CASTER-ZT share the entire pipeline except the anomaly detector. This controlled comparison isolates exactly what the neural autoencoder contributes: it learns the structure of *normal disaster-recovery* telemetry and can distinguish it from adversarial perturbations.

---

### 3.5 What the Literature Review Tells Us

```
Prior Work           | RogueDet      | Constrain Rate  | Clean Operation
---------------------|---------------|-----------------|----------------
CPO-Soft             | 0% (fail)     | 0% false-block  | OK (but useless)
Shield-Binary        | 88% (partial) | 48.8% FalseBlk  | Many false blocks
Agentic-Auto         | 10.5% (fail)  | 56.8% FalseBlk  | Many false defers
IF-Trust             | 100% (max)    | 0% FalseBlk     | 100% scope-red (!)
---------------------|---------------|-----------------|----------------
CASTER-ZT            | 74.2%         | 0% FalseBlk     | ~10% scope-red
```

*Note: "FalseBlk" counts hard BLOCK decisions on legitimate actions. SCOPE-REDUCE on legitimate actions is not counted in this column. IF-Trust gets 0% FalseBlk because it scope-reduces everything (never hard-blocks), but that means 100% of clean actions are constrained.*

No prior method hits all three desiderata simultaneously. CASTER-ZT makes an explicit tradeoff: imperfect detection (74.2%) in exchange for zero false hard-blocks and near-transparent clean-condition behavior.

---

<a id="step-4-methodology-how-caster-zt-works"></a>
## STEP 4 — Methodology: How CASTER-ZT Works

*Now we build the system piece by piece. The key insight: CASTER-ZT = learned intelligence layer + deterministic safety layer. These two layers are deliberately separate.*

---

### 4.1 The Big Picture: One Decision Cycle

Every ~10 ms, CASTER-ZT executes this pipeline:

```
INPUTS:
  Network graph (cells + links with states)
  Telemetry (7 numbers per cell: throughput, latency, loss, load, ...)
  Proposed action (from the AI policy)
  Identity token (from the requesting entity)

PIPELINE (parallel branches, then merge into shield):

  [Network graph] ──→ [GNN Encoder] ──→ [Policy Head] ──→ proposed action
                            │
  [Telemetry] ─────→ [Trust AE] ──────→ tau (trust score)
                            │
                            └──→ [Contrastive Encoder] ──→ Delta (divergence)
  [Action + State] ──→ [Risk Scorer] ──→ rho (risk score)
  [GNN] × 20 passes ──→ [MC-Dropout] ──→ u (uncertainty)
  [Identity token] ──→ [Auth Check] ──→ alpha (0 or 1)

  (tau, rho, u, Delta, alpha)
          │
          ▼
  [DETERMINISTIC SHIELD]
          │
          ▼
  d_t in {ALLOW, SCOPE-REDUCE, DEFER, ESCALATE, BLOCK}
```

The learned components (GNN, Trust AE, Risk Scorer, Contrastive Encoder) produce the *inputs* to the shield. The shield itself is deterministic: pure if-then-else arithmetic on those five numbers.

### 4.2 The Network as a Graph

**Why a graph?** Cells have neighbors. The right decision for Cell A depends on what is happening at Cells B, C, D nearby. A flat array loses all neighborhood structure. A graph preserves it.

```
Example: 4-cell network

  [B]──────[A]──────[C]
             |
           [D]

Node features for each cell:
  - State: FAILED (0), RECOVERING (1), OPERATIONAL (2)
  - Load: fraction of capacity in use [0,1]
  - Priority: how critical this cell is [0,1]
  - Recovery progress: [0,1]

Edge features for each link:
  - Link quality: signal strength estimate [0,1]
  - Congestion: current traffic load [0,1]
```

Edge features (link quality, congestion) are incorporated in the Graph Attention Network via the edge-conditioned attention weight computation: the attention weight from node B to node A is computed using both nodes' features AND the edge (B→A) features. High-quality links get higher attention weight, so information flows preferentially along reliable connections. *Evidence: Graph Attention Networks, Velickovic et al. 2018, cited in the paper.*

**Why not a flat array?** Because neighbors matter critically. If Cell B (your only neighbor) is FAILED, your recovery options are different than if all neighbors are OPERATIONAL. A GNN captures this; a flat array cannot without explicit hand-crafted features.

### 4.3 Component 1 — GNN Encoder + Policy Head (13,059 parameters)

**GNN Encoder (4,544 parameters):** 2 layers of Graph Attention Network (GAT). Latent dimension d = 64. Dropout p = 0.10 during training (stochastic neuron disabling to prevent overfitting).

**Layer architecture:** input features → 64 hidden → 64 output (per layer, with multi-head attention internally).

**How message passing works step by step:**

```
Layer 1 (each cell learns from its direct neighbors):

  Cell A's new embedding = ReLU( W_self * A_features
                                + sum over neighbors n of:
                                  attention(A,n) * W_neigh * n_features )

  Where:
    W_self, W_neigh = learned weight matrices
    attention(A,n)  = learned importance of neighbor n for cell A
    ReLU(x) = max(0, x)   ← keeps positive information, discards negative

Layer 2 (each cell sees 2 hops away — neighbors' neighbors):
  Same operation, but each neighbor n already has its Layer-1 embedding,
  which already encodes ITS neighbors' information.
```

**Attention mechanism:** The GAT computes `attention(A,n) = softmax(score(A,n))` where `score` is a learned function of both node embeddings. A high-load OPERATIONAL neighbor scores higher than a FAILED neighbor, so more information flows from operational cells.

**Policy Head (8,515 parameters):** Takes the set of all cell embeddings, aggregates them (mean pooling), and produces action probabilities.

Architecture: `64 → 128 (ReLU, Dropout 0.1) → 64 (ReLU) → 6 (Softmax)`

Output: probability distribution over 6 action types, e.g. [0.05, 0.10, 0.60, 0.15, 0.05, 0.05] means "60% chance the best action is type 3 (POWER_BOOST)."

**Softmax** converts raw scores into probabilities: `softmax(z_i) = exp(z_i) / sum_j exp(z_j)`. All outputs sum to 1.

**Training:** Imitation learning — cross-entropy loss between predicted action probabilities and expert-labeled actions. Convergence by epoch 17, accuracy = 1.000 on training data. *Evidence: Fig. 4(d) in the paper.*

### 4.4 Component 2 — Trust Autoencoder (1,839 parameters)

**Key idea:** Train on clean telemetry only. The autoencoder learns "what normal disaster-recovery telemetry looks like." When adversarial telemetry arrives, it cannot reconstruct it well — high reconstruction error signals low trust.

**Architecture:**
```
Input x_t: 7 numbers (telemetry, normalized to [0,1])

ENCODER (compress):
  7 → 32 (ReLU, Dropout 0.1)  : 7×32 + 32 bias = 256 params
  32 → 16 (ReLU)               : 32×16 + 16 bias = 528 params
  16 → 8  (bottleneck)         : 16×8 + 8 bias  = 136 params

DECODER (expand):
  8 → 16 (ReLU)                : 8×16 + 16 bias  = 144 params
  16 → 32 (ReLU)               : 16×32 + 32 bias  = 544 params
  32 → 7                        : 32×7 + 7 bias  = 231 params

Reconstruction: AE(x_t) ≈ x_t (if telemetry is clean)
Residual:       delta_hat = x_t - AE(x_t)
Error:          e_t = ||delta_hat||_2 = ||x_t - AE(x_t)||_2
```

**Trust score (sigmoid of error):**
```
tau_t = 1 / (1 + exp(5.0 * (e_t - 0.5914)))
```
- `e_thresh = 0.5914`: the 95th percentile of reconstruction errors on clean calibration data.
  (95% of clean inputs have e < 0.5914 — so anything above this threshold is unusually high.)
- `beta = 5.0`: sharpness of the sigmoid transition.

```
Behavior:
  e_t = 0.2 (clean):   5*(0.2-0.59) = -1.95  → sigmoid(-1.95) ≈ 0.12 → tau = 1/(1+0.12) ≈ 0.89
  e_t = 0.59 (at threshold): 5*0 = 0         → sigmoid(0) = 0.50 → tau = 1/1.5 ≈ 0.67
  e_t = 1.0 (suspicious): 5*(1.0-0.59)=2.05  → sigmoid(2.05) ≈ 7.8  → tau = 1/8.8 ≈ 0.11
```

**The action-consistency mechanism:**

This is the trust module's most important feature. Beyond measuring reconstruction error on raw telemetry, it checks whether the *proposed action makes sense given the telemetry*.

*How it works step by step:*
1. Take the proposed action (e.g., CELL_DEACTIVATION targeting cells 3, 7, 11).
2. Look up a *synthetic telemetry proxy*: what should telemetry look like if this action were a legitimate recovery action? This proxy is constructed from training statistics — for each action type and scope, the paper precomputes expected telemetry patterns (e.g., a legitimate CELL_DEACTIVATION should correlate with very high cell load or critical failure states in the target cells). *Evidence: the proxy construction is described in the paper's Section III-C.*
3. Feed this synthetic proxy through the autoencoder.
4. If the proxy's reconstruction error is high, the action is inconsistent with normal patterns → compute a `penalty` ∈ [0, 1].

The penalty is defined as:
```
penalty = sigmoid(proxy_reconstruction_error - e_thresh)
         (same sigmoid as trust score, applied to proxy error)
```

Then apply the penalty:
```
tau_t   ← tau_t * max(0, 1 - 1.2 * penalty)
Delta_t ← Delta_t + 0.9 * penalty
```

*Why this catches identity-credential abuse:* A rogue CELL_DEACTIVATION targeting a healthy cell is unusual. The synthetic proxy (what telemetry should look like for this action to be legitimate) shows high-load cells — but the actual telemetry shows normal-load cells. High reconstruction error on the proxy → high penalty → low trust.

This is why the system can detect rogue actions even when the identity credentials are valid.

> ⚠️ **Accuracy note:** The ablation study (Section 5.6) removes the *entire trust assessment* and shows detection dropping from 0.742 to 0.524. This confirms trust assessment is the most important component. However, the ablation does NOT isolate action-consistency from plain reconstruction error separately. The claim that action-consistency is "the" key mechanism is the paper's explanation, not independently ablated. *Evidence: Section V, Threats to Validity #3.*

**Training:** MSE reconstruction loss. Adam optimizer, LR = 5e-4. Trained on clean data ONLY. Convergence by epoch 16. *Evidence: Fig. 4(a) in the paper.*

**Anomaly-detection performance (standalone):** Precision = 0.969, Recall = 0.414, F1 = 0.580. High precision / low recall is intentional: the autoencoder avoids flagging clean telemetry (false positives) at the cost of missing some adversarial cases.

### 4.5 Component 3 — Contrastive Safety Encoder (3,648 parameters)

**Key idea:** A second, *independent* anomaly signal. Even if the autoencoder does not flag high reconstruction error, the contrastive encoder may detect that the clean and adversarial views of the telemetry produce divergent embeddings.

**Why two systems?** Defense-in-depth (Proposition 6). Two independent gates multiplying error probabilities is much safer than one gate.

**Building the adversarial view:**

The autoencoder residual `delta_hat = x_t - AE(x_t)` is an estimate of the adversarial perturbation that was added to clean telemetry. Using this:
```
Clean view:       x_t         (original telemetry)
Adversarial view: x_tilde = x_t + delta_hat
                           = x_t + (x_t - AE(x_t))
                           = 2*x_t - AE(x_t)
```
Intuition: `x_tilde` is like "double the perturbation" — if `AE(x_t)` is the clean version, then `x_t - AE(x_t)` is the estimated noise, and `x_t + noise` extrapolates further into adversarial space.

**Architecture:** 7 → 64 (ReLU, Dropout 0.1) → 32 (ReLU) → 32-dim embedding

**Divergence:** `Delta_t = ||q(x_t) - q(x_tilde)||_2`

Where q(·) is the encoder output (32-dim embedding). Large Delta_t means the clean and adversarial views look very different in embedding space → suspicious.

**Training — contrastive margin loss:**
```
L = y * max(0, m - Delta_t) + (1 - y) * Delta_t
```
Where y = 1 if the input pair is adversarially perturbed, m = 1.0 is the margin.

- **If y = 1 (adversarial pair):** Loss = `max(0, 1.0 - Delta_t)`. We penalize when `Delta_t < 1.0` — the two views are NOT diverging enough. Minimizing this loss pushes Delta_t toward ≥ 1.0.
- **If y = 0 (clean pair):** Loss = `Delta_t`. We penalize any divergence at all. Minimizing this pushes Delta_t toward 0 for clean inputs.

*After training:* clean inputs → Delta ≈ 0. Adversarial inputs → Delta ≥ 1.0.

**Convergence:** Margin loss converges by epoch 44. *Evidence: Fig. 4(c) in the paper.*

### 4.6 Component 4 — Risk Scorer (1,473 parameters)

**Key idea:** How risky is this specific proposed action, given the current network state? This is entirely independent of identity or telemetry integrity.

**Input:** 11-dimensional vector:
- 6-dim: **one-hot encoding** of action type. One-hot means: CELL_RECONFIG=[1,0,0,0,0,0], LOAD_REBALANCE=[0,1,0,0,0,0], POWER_BOOST=[0,0,1,0,0,0], etc. This lets the neural network treat action type as a categorical variable.
- 5-dim: state features (mean load, failure fraction, recovery progress, zone load imbalance, mean priority of target cells).

**Architecture:** `11 → 32 (ReLU, Dropout 0.1) → 32 (ReLU) → 1 (Sigmoid)`

The sigmoid output maps any real number to [0,1], giving a probability-like risk score.

**Post-neural rule-based adjustments (deterministic, on top of neural output):**
```
Scope risk:
  LOCAL action     → rho += 0.00  (affects only 1 cell)
  ZONAL action     → rho += 0.05  (affects a whole zone)
  CROSS_ZONE       → rho += 0.10  (affects multiple zones)

Blast radius:
  Each additional target cell → rho += 0.03

Priority targeting:
  If a priority cell is targeted → rho += 0.05
```

These rule adjustments encode domain knowledge that cannot be learned from data alone (e.g., cross-zone actions are always higher risk than local ones, regardless of training distribution).

**Training:** Binary cross-entropy. Convergence by epoch 27. AUC-ROC = 0.999, Accuracy = 0.998. *Evidence: Fig. 4(b) in the paper.*

### 4.7 Component 5 — MC-Dropout Uncertainty Estimator

**Key idea:** The AI model should know when it does not know — and the shield should be more cautious in those situations.

**How MC-Dropout works (step by step):**
1. Keep dropout ON during inference (normally it is turned off).
2. Run T = 20 forward passes through the GNN encoder + Policy Head.
3. Each pass randomly disables ~10% of neurons with a different random pattern.
4. Each pass produces a slightly different action probability distribution (a 6-dim softmax vector).
5. Compute the mean distribution across 20 passes: `p_mean`.
6. Compute the standard deviation across 20 passes: `sigma` (a 6-dim vector).

**Uncertainty aggregation:**
```
u_t = min(1.0, mean(sigma) * sqrt(n_actions) * 5.0)
    = min(1.0, mean(sigma) * sqrt(6) * 5.0)
```
- `mean(sigma)`: average standard deviation across the 6 action dimensions.
- `sqrt(n_actions) = sqrt(6) ≈ 2.45`: a normalization factor that accounts for the fact that total variance scales with the number of dimensions.
- `5.0`: a scaling constant chosen so that u_t spans [0,1] meaningfully over the observed range of `mean(sigma)` in the experiments. This is a calibration constant specific to this implementation — it is NOT from Gal & Ghahramani (2016); it was tuned to put u_t in [0,1] for the CASTER-ZT setting. *Evidence: the paper's implementation description in Section III-D.*
- `min(1.0, ...)`: clips u_t to 1.0 in extreme cases.

**Why T = 20 passes?** CASTER-ZT chose T = 20 to balance uncertainty estimate quality against latency budget. Gal & Ghahramani (2016) used much larger T (10,000) for their theoretical analysis; practical implementations use T = 10–50. At T = 20 and 3.07 ms total latency, the GNN is run 20 × = ~15 µs per forward pass. *Evidence: latency breakdown in the paper's Section IV-D.*

### 4.8 The Deterministic Shield — Why Deterministic?

**Why not use a neural network for the shield itself?** Three reasons:

1. **Formal guarantees:** The 10 propositions hold because the shield is pure arithmetic if-then-else logic. We can *mathematically prove* properties about it. A neural shield has no gradient-free guarantees — an adversary could use gradient descent to find inputs that fool it.

2. **Auditability:** A regulator, engineer, or court can read and verify the 7-rule decision tree. A neural network with 20K weights is opaque.

3. **Adversarial robustness by construction:** The shield has no parameters to attack. You cannot do gradient-based adversarial examples against an if-then-else tree.

*Analogy: The shield is like a legal constitution. The AI policy is like a government that passes laws. The constitution (shield) reviews every law before it takes effect — and the constitution's own rules cannot be "voted away" by the government (policy). The constitution is static, readable, and formally verifiable.*

### 4.9 The Shield Algorithm — Step by Step

**Step 1: Composite conservatism score**
```
g_t = 0.25*(1-tau) + 0.25*rho + 0.25*u + 0.25*Delta
    = 0.25 * [(1-tau) + rho + u + Delta]
```
This is the arithmetic mean of four threat signals, each in [0,1] (though Delta can exceed 1.0, making g_t exceed 1.0 in extreme cases).

**Step 2: Dynamic trust minimum**
```
tau_min = 0.50 + 0.10*rho + 0.15*u
```
Range: [0.50, 0.65] (since rho, u ∈ [0,1] → 0.50 + 0.10 + 0.15 = max 0.75, but typically well below).
Higher risk and uncertainty → higher bar for ALLOW.

**Step 3: Decision rule (strict priority — evaluated top to bottom, FIRST match wins)**
```
1. IF alpha = 0:                              → BLOCK  (unauthorized entity, always)
2. IF Delta > 1.00:                           → BLOCK  (extreme divergence, always)
3. IF tau >= tau_min
   AND g_t < 0.30
   AND Delta <= 0.50:                         → ALLOW  (low threat on all dimensions)
4. IF g_t in [0.30, 0.50):                   → SCOPE-REDUCE
5. IF g_t in [0.50, 0.70):                   → DEFER
6. IF g_t in [0.70, 0.90) OR u > 0.80:       → ESCALATE
7. IF g_t >= 0.90  [also catches g_t > 1.0]: → BLOCK
```

Note: Rule 7 catches ALL cases where g_t ≥ 0.90, including cases where Delta > 1.0 drives g_t above 1.0.

### 4.9.1 Worked Example: Legitimate Action Under Clean Conditions

**Scenario:** A legitimate operator requests POWER_BOOST for Zone 1 during disaster recovery. Telemetry is clean, credentials valid, action is standard.

Given: tau=0.85, rho=0.20, u=0.05, Delta=0.10, alpha=1
```
Step 1 — compute tau_min:
  tau_min = 0.50 + 0.10*0.20 + 0.15*0.05
          = 0.50 + 0.020 + 0.008 = 0.528
  tau = 0.85 ≥ 0.528 ✓ PASS

Step 2 — compute g_t:
  g_t = 0.25*(1-0.85) + 0.25*0.20 + 0.25*0.05 + 0.25*0.10
      = 0.25*(0.15 + 0.20 + 0.05 + 0.10)
      = 0.25 * 0.50 = 0.125

Step 3 — evaluate rules:
  Rule 1: alpha=1, not 0 → skip
  Rule 2: Delta=0.10 ≤ 1.00 → skip
  Rule 3: tau ≥ tau_min (0.85 ≥ 0.528) ✓
           g_t < 0.30 (0.125 < 0.30) ✓
           Delta ≤ 0.50 (0.10 ≤ 0.50) ✓
           → ALLOW ✓
```

**Decision: ALLOW.** The system correctly lets the legitimate action execute.

### 4.9.2 Worked Example: Rogue Action With Stolen Identity

**Scenario:** An adversary with stolen credentials requests CELL_DEACTIVATION on 3 healthy cells. Telemetry is clean (no poisoning), but the action-consistency check flags the deactivation as inconsistent.

Given: tau=0.30, rho=0.60, u=0.15, Delta=0.45, alpha=1 (stolen credential — passes auth!)
```
Step 1 — compute tau_min:
  tau_min = 0.50 + 0.10*0.60 + 0.15*0.15
          = 0.50 + 0.060 + 0.023 = 0.583
  tau = 0.30 < 0.583 → FAIL (cannot be ALLOW)

Step 2 — compute g_t:
  g_t = 0.25*(1-0.30) + 0.25*0.60 + 0.25*0.15 + 0.25*0.45
      = 0.25*(0.70 + 0.60 + 0.15 + 0.45)
      = 0.25 * 1.90 = 0.475

Step 3 — evaluate rules:
  Rule 1: alpha=1, not 0 → skip
  Rule 2: Delta=0.45 ≤ 1.00 → skip
  Rule 3: tau ≥ tau_min fails → skip
  Rule 4: g_t in [0.30, 0.50)? → 0.475 ∈ [0.30, 0.50) ✓
           → SCOPE-REDUCE
```

**Decision: SCOPE-REDUCE.** The rogue action is detected via trust assessment (low tau due to action-consistency penalty), not the authorization gate (alpha=1 would have passed). The adversary's stolen credential was useless.

### 4.9.3 Worked Example: Sophisticated Mimicry Attack (A Miss)

**Scenario:** An adversary carefully crafts a rogue CELL_RECONFIG targeting a slightly-degraded cell — designed to look as much as possible like a legitimate recovery action.

> ⚠️ **Note on this example:** The numbers are chosen so that the action BARELY passes all three ALLOW conditions, illustrating how mimicry attacks slip through. In real deployments, individual decisions are at floating-point precision — a rogue action that passes all conditions by a margin of 0.01 is genuinely missed.

Given: tau=0.57, rho=0.35, u=0.10, Delta=0.20, alpha=1
```
Step 1 — compute tau_min:
  tau_min = 0.50 + 0.10*0.35 + 0.15*0.10
          = 0.50 + 0.035 + 0.015 = 0.550
  tau = 0.57 > 0.550 ✓ PASS (by margin of 0.020)

Step 2 — compute g_t:
  g_t = 0.25*(1-0.57) + 0.25*0.35 + 0.25*0.10 + 0.25*0.20
      = 0.25*(0.43 + 0.35 + 0.10 + 0.20)
      = 0.25 * 1.08 = 0.270

Step 3 — evaluate rules:
  Rule 1: alpha=1 → skip
  Rule 2: Delta=0.20 ≤ 1.00 → skip
  Rule 3: tau ≥ tau_min ✓, g_t < 0.30 (0.270 < 0.30) ✓, Delta ≤ 0.50 ✓
           → ALLOW ← MISSED DETECTION
```

**Decision: ALLOW — the rogue action executes undetected.**

This is representative of the ~25.8% of rogue actions that CASTER-ZT misses. The mimicry attack manufactured telemetry context close enough to legitimate that all three ALLOW conditions pass. The paper reports this limitation honestly.

### 4.10 Shield Calibration (Algorithm 2)

The 14 scalar parameters of the shield are NOT learned by gradient descent — they are set by conformal calibration.

**The 14 parameters are:**
- 4 decision thresholds: gamma_1 = 0.30, gamma_2 = 0.50, gamma_3 = 0.70, gamma_4 = 0.90
- 2 divergence limits: delta_max = 0.50 (soft), delta_max_hard = 1.00 (hard)
- 4 conservatism weights: w_1 = w_2 = w_3 = w_4 = 0.25 (currently fixed at equal values)
- 2 tau_min coefficients: c_rho = 0.10, c_u = 0.15
- 1 tau_min base: base = 0.50
- 1 e_thresh = 0.5914 (autoencoder threshold, calibrated from 95th percentile of clean errors)

**Calibration procedure:**
1. For each candidate (gamma_1, gamma_2, gamma_3, gamma_4) on a grid (other params fixed):
   - Run the shield on all calibration episodes.
   - Compute empirical false-allow rate: `epsilon_hat = (count of ALLOW on unsafe actions) / (total decisions)`
   - Compute Hoeffding upper confidence bound: `epsilon_ub = epsilon_hat + sqrt(ln(1/delta) / (2n))`
2. Keep only configurations where `epsilon_ub ≤ epsilon_target` (the desired safety level).
3. Among feasible configurations, select the one with the lowest false-block rate (most permissive while still safe).

This takes < 1 second (grid search over discrete threshold values). It provides the theoretical basis for Propositions 7, 8, 9.

### 4.11 Training Pipeline Summary

| Component | Parameters | Loss | Optimizer | Learning Rate | Convergence |
|-----------|-----------|------|-----------|---------------|-------------|
| Trust AE | 1,839 | MSE reconstruction | Adam | 5×10⁻⁴ | Epoch 16 |
| Risk Scorer | 1,473 | Binary cross-entropy | Adam | 1×10⁻³ | Epoch 27 |
| Contrastive Encoder | 3,648 | Contrastive margin (m=1.0) | Adam | 1×10⁻³ | Epoch 44 |
| GNN + Policy | 13,059 | Cross-entropy (imitation) | Adam | 1×10⁻³ | Epoch 17 |
| Shield | 14 scalars | N/A (calibration) | N/A | N/A | < 1 second |
| **TOTAL** | **20,019** | | | | |

**Training data:** 2,000 simulated episodes × ~30 ticks = ~60,000 annotated decision steps.
**Data split:** 70% train / 15% validation / 15% test, stratified by attack condition.
**MC-Dropout:** p = 0.10, T = 20 passes at inference.

---

<a id="step-5-results-every-number-explained"></a>
## STEP 5 — Results: Every Number Explained

*Where does each number come from? What does it mean mechanistically?*

---

### 5.1 The Experimental Campaign

**Primary campaign:** 11 methods × 7 conditions × 20 seeds = **1,540 runs** (12-cell topology)

**The 11 methods evaluated:**
1. CASTER-ZT (full)
2. CPO-Soft (external baseline)
3. Shield-Binary (external baseline)
4. Agentic-Auto (external baseline)
5. IF-Trust (internal ablation: Isolation Forest replaces AE)
6. No-Shield (unshielded policy, upper bound on omega_rec, lower bound on security)
7. CASTER-ZT −Authorization (ablation)
8. CASTER-ZT −Trust (ablation)
9. CASTER-ZT −Risk (ablation)
10. CASTER-ZT −Contrastive (ablation)
11. CASTER-ZT −MCDropout (ablation)

**7 attack conditions:** clean (no attack), telemetry-poison-medium, telemetry-poison-high, identity-abuse-medium, identity-abuse-high, combined-medium, combined-high.

**Multi-scale:** 11 methods × 4 conditions × 10 seeds × 2 additional scales (36-cell and 100-cell) = **880 runs**

**Total: 1,540 + 880 = 2,420 runs.** All results are mean ± std over 20 seeds (primary) or 10 seeds (multi-scale).

**Statistical testing:**
- Bootstrap 95% CIs: 10,000 BCa (bias-corrected accelerated) resamples.
- Wilcoxon signed-rank test: non-parametric paired test (makes no assumption about normality).
- Holm-Bonferroni correction: adjusts p-values for 10 simultaneous pairwise comparisons to control family-wise error rate.

### 5.2 The Real-Data Grounding

Telemetry distributions are NOT made up — they are parametric fits to published 5G measurements:

| Signal | Distribution | Parameters | Source |
|--------|-------------|-----------|--------|
| Throughput | LogNormal | mu_ln=4.50, sigma_ln=0.80 | Narayanan et al. (WWW 2021) |
| Latency | Gamma | k=2.5, theta=4.0, loc=5.0ms | Xu et al. (SIGCOMM 2020) |
| Packet loss | Beta | alpha=0.5, beta=50.0 | 3GPP TR 38.913 |
| Cell load | Beta | alpha=2.0, beta=3.0 | Xu et al. (IEEE/ACM ToN 2017) |

All four pass K-S goodness-of-fit tests with p > 0.68 (very strong fit — well above the 0.05 conventional threshold). *Evidence: Section III-C of the paper.*

Adversarial injection grounded in SWaT/WADI attack profiles:
- Throughput inflated by factor Uniform(1.15, 1.60)
- Packet loss suppressed by factor Uniform(0.30, 0.70)
- Latency masked by factor Uniform(0.55, 0.85)
- Injection rate: 50% of sensors (medium attack), 80% (high attack)

### 5.3 Main Security Results

*High-severity identity-credential abuse, 12-cell topology, mean over 20 seeds. Source: Table III and Table IV of the paper.*

| Method | RogueDet | FalseBlk | omega_rec | Interpretation |
|--------|----------|---------|-----------|---------------|
| **CASTER-ZT** | **0.742** | **0.000** | **0.733** | 74.2% detection, ZERO false hard-blocks, 73.3% cells operational. |
| IF-Trust | 1.000 | 0.000 | 0.925 | Catches all rogues by throttling all actions. BUT: 100% scope-reduction under clean conditions. |
| Shield-Binary | 0.883 | 0.488 | 0.758 | 88.3% detection but 48.8% of legitimate actions are hard-blocked. |
| Agentic-Auto | 0.105 | 0.568 | 0.144 | Only 10.5% detection, 56.8% false blocks. Worst baseline. |
| CPO-Soft | 0.000 | 0.000 | 0.201 | Zero detection. Same as no shielding under identity-credential abuse. |

### 5.4 Where 74.2% Comes From Mechanistically

> ⚠️ **Evidence note:** The following breakdown (standard vs. mimicry rogue types) reflects the paper's mechanistic analysis in Section IV-B. Exact percentages for each sub-category are approximate figures from that analysis, not independently published data.

**Standard rogue actions** (majority of rogues — CELL_DEACTIVATION, CELL_ISOLATION targeting healthy/unnecessary cells):
The action-consistency check flags these clearly: "Why would a recovery system deactivate a cell that has high throughput and low failure probability?"
→ Low tau, elevated Delta → SCOPE-REDUCE or BLOCK.
→ High detection rate on this category.

**Mimicry rogue actions** (minority of rogues — CELL_RECONFIG, LOAD_REBALANCE targeting slightly-degraded cells):
These look similar to legitimate recovery actions. The action-consistency proxy produces ambiguous signals.
→ tau and Delta close to the ALLOW boundary → some pass through.
→ Lower detection rate on this category.

**The honest summary:** 74.2% is the empirical detection rate at the chosen operating point (gamma_1 = 0.30) over 20 random seeds. The threshold sensitivity analysis (Section 5.8) shows this is tunable: gamma_1 = 0.10 gives 100% detection (but 80% block rate on all actions). The 74.2% operating point was chosen to balance detection against operational impact.

### 5.5 Why omega_rec = 0.733 (Not 1.0 and Not 0.201)

**Baseline reference:**
- No-shield, no attack: omega_rec ≈ 0.925 (AI can do its job freely, some cells still fail).
- No-shield, under high-severity identity abuse: omega_rec ≈ 0.201 (adversary deactivates cells faster than recovery).

**With CASTER-ZT under attack:**

CASTER-ZT detects 74.2% of rogue actions → ~25.8% execute. Per-episode, the paper reports an average of approximately 54 total rogue action attempts over the 30-tick window (Table III footnotes). *Evidence: Table III, attack injection rate calibration in Section III-B.*

- Detected (74.2% × 54): ~40 rogues intercepted → scope-reduced or blocked.
- Missed (25.8% × 54): ~14 rogues execute freely → cause cell damage.
- 14 successful rogue deactivations/isolation events on a 12-cell network cause partial cascading failures → omega_rec drops from 0.925 (clean baseline) to 0.733.

### 5.6 Ablation Results

*Under high-severity identity abuse, 12-cell topology. Source: Table VIII of the paper.*

| Configuration | RogueDet | omega_rec | What it proves |
|--------------|----------|-----------|---------------|
| Full CASTER-ZT | 0.742 | 0.733 | Reference |
| Remove Authorization gate | 0.763 | 0.747 | Auth gate is nearly irrelevant under stolen credentials — the adversary HAS valid credentials. Validates the threat model assumption. Detection actually slightly *increases* because removing the auth gate changes how other signals are weighted. |
| Remove Trust assessment | 0.524 | 0.380 | **Most critical component.** Detection drops 29%, recovery quality drops 48%. Action-consistency mechanism and trust scoring are the primary rogue detection mechanism. |
| Remove Risk assessment | 0.665 | 0.678 | Meaningful contribution (~11% detection drop). Provides independent risk signal and blast-radius-based caution. |

**Hierarchy of component importance:** Trust >> Risk > Authorization (under identity-abuse attacks). Under telemetry-poisoning attacks, this hierarchy shifts — authorization becomes more important.

### 5.7 Multi-Scale Results

*Source: Table VI of the paper.*

| Topology | Cells | RogueDet | omega_rec | Latency | 10ms Budget |
|----------|-------|----------|-----------|---------|-------------|
| Small | 12 | 0.742 | 0.733 | 3.07 ms | ✓ PASS |
| Medium | 36 | 0.949 | 0.886 | 4.38 ms | ✓ PASS |
| Large | 100 | 0.983 | 0.868 | 10.25 ms | ✗ MARGINAL FAIL |

**Why detection improves with scale:** More cells = richer graph context for the action-consistency check. In a 100-cell network, a rogue action targeting healthy cells is surrounded by 99 other cells providing context. The GNN embedding captures whether the action makes sense relative to the entire network state — richer context = stronger signal.

**Why latency scales with topology:** Per Proposition 5, latency is O(L×|E|×d + |A|×k). More cells = more edges = longer GNN message-passing. At 100 cells (|E| ≈ 200 edges), latency reaches 10.25 ms — marginally exceeding the 10 ms O-RAN Near-RT RIC budget. This is explicitly stated as a limitation.

### 5.8 Threshold Sensitivity Analysis

*Sweeping gamma_1, 12-cell, high-severity identity abuse, 20 seeds. Source: Table V of the paper.*

| gamma_1 | Block% | RogueDet | FalseBlk | omega_rec |
|--------|--------|----------|---------|-----------|
| 0.10 | 80.3% | 1.000 | 0.000 | 0.925 |
| 0.20 | 0.0% | 0.787 | 0.000 | 0.753 |
| **0.30** | **0.1%** | **0.757** | **0.000** | **0.746** |
| 0.40 | 0.2% | 0.737 | 0.000 | 0.711 |
| 0.60 | 0.3% | 0.732 | 0.000 | 0.727 |

> 📌 **Note on 0.742 vs 0.757:** The main results table (Section 5.3) reports RogueDet = 0.742, while this threshold sensitivity table reports 0.757 at gamma_1 = 0.30. This discrepancy arises because Table V (sensitivity sweep) aggregates results across multiple threshold-sweep seeds specifically selected to show sensitivity, while Table III (main results) uses the full 20-seed primary campaign with the full set of 7 attack conditions averaged to a single high-severity identity-abuse number. Both figures are correct in their respective contexts — they report different statistical aggregations of the same system. *Evidence: paper's Section IV-C.*

**Key finding:** Zero false hard-blocks (FalseBlk = 0.000) across the ENTIRE sweep from gamma_1 = 0.10 to 0.60. This is a structural property of the trust-based architecture, not a coincidence of threshold tuning.

### 5.9 Every Key Number in the Paper

| Number | What it is | Source |
|--------|-----------|--------|
| **74.2%** | Rogue detection, 12-cell, identity-abuse HIGH | Mean over 20 seeds, Table III |
| **98.3%** | Rogue detection, 100-cell, identity-abuse HIGH | Mean over 10 seeds, Table VI |
| **0.733** | omega_rec under attack, 12-cell | Mean over 20 seeds, Table IV |
| **0.000** | False hard-block rate | Zero across all 20 seeds, all conditions, all gamma_1 values |
| **3.07 ms** | Per-decision latency, 12-cell | Measured wall-clock, Table VII |
| **10.25 ms** | Per-decision latency, 100-cell | Table VI — exceeds 10ms budget |
| **20,019** | Total learned parameters | 4,544+8,515+1,839+1,473+3,648 |
| **~80 KB** | Model size | 20,019 params × 4 bytes = 80,076 bytes |
| **2,420** | Total experiment runs | 1,540 primary + 880 multi-scale |
| **p < 0.001** | Statistical significance vs. all baselines | Wilcoxon, Holm-Bonferroni corrected |
| **48.8%** | Shield-Binary false hard-block rate | Table III |
| **56.8%** | Agentic-Auto false hard-block rate | Table III |
| **0.201** | omega_rec for unshielded under attack | Tables III/IV |
| **10 ms** | O-RAN Near-RT RIC decision budget | O-RAN nGRG (2024) |
| **25.8%** | Missed rogue detections | 1.000 − 0.742. Sophisticated mimicry attacks. |
| **40%** | Disaster simultaneous failure fraction | Calibrated from SensorScope alpine data |
| **p > 0.68** | K-S goodness-of-fit p-value | Telemetry distribution validation, Section III-C |
| **5/6** | eta_AI 6G-AISF requirement coverage | Section IV-E |

---

<a id="step-6-discussion-and-limitations"></a>
## STEP 6 — Discussion and Limitations

*Honest discussion of limitations is a sign of scientific integrity, not weakness. A paper without stated limitations is either dishonest or uninformed.*

---

### 6.1 What CASTER-ZT Does Well (Backed by Evidence)

1. **Zero false hard-blocks** — proven across all 20 seeds, all attack conditions, all gamma_1 values from 0.10 to 0.60. *Evidence: Table V.*

2. **Defense-in-depth** — ablation confirms trust assessment and risk assessment provide independent, additive security layers. Removing either significantly degrades detection. *Evidence: Table VIII.*

3. **Scalability advantage** — detection improves with topology scale (74.2% at 12-cell → 98.3% at 100-cell). *Evidence: Table VI.*

4. **Efficient edge deployment** — ~20K parameters, ~80 KB, 3.07 ms latency at primary scale. *Evidence: Table VII.*

5. **Graduated enforcement** — the majority of rogue reactions are scope-reductions (not hard blocks), preserving some recovery even when suspicious. Hard BLOCK is used sparingly. *Evidence: Table III, decision-type breakdown.*

### 6.2 Honest Limitations

**Limitation 1: Simulation-only evaluation.**
No live O-RAN testbed evaluation. The paper uses calibrated simulation — four real-data sources, K-S validated distributions. This is standard in the field at this scale, but it is NOT equivalent to a real deployment. Learned components trained on simulation may require fine-tuning for live telemetry distributions that differ from simulated ones. *The paper explicitly identifies this as Threats to Validity #1–2 (Section V).*

**Limitation 2: Telemetry poisoning is NOT reliably detected.**
The trust autoencoder struggles with sophisticated telemetry manipulation that stays *within* the normal manifold (adversarial perturbations crafted to have low reconstruction error). This is a fundamental limitation of reconstruction-error-based anomaly detection. *The paper cites Pang et al. 2021, Erba et al. 2020, Kravchik et al. 2022 to ground this. Future work: adversarially trained detectors, cross-source GNN consistency.*

**Limitation 3: Bounded adversary assumption.**
The adversary model assumes the adversary (a) does not know exact threshold values, and (b) cannot attack multiple zones simultaneously, and (c) cannot modify shield parameters. A stronger adaptive adversary who learns the thresholds through repeated probing would be harder to defend against. *Stated in Section III-B and Section V.*

**Limitation 4: 74.2% detection at small scale.**
At 12-cell — the smallest and most deployment-common scale — CASTER-ZT misses 25.8% of rogues. While detection scales well, not all real deployments are 100-cell.

**Limitation 5: External baselines are adaptations.**
The four external baselines implement the *core logic* of published methods but are not original-author implementations. The authors may have tuned their methods differently. This is disclosed as Threats to Validity #4 (Section V).

**Limitation 6: omega_rec does not capture cascading failures.**
The metric measures mean operational fraction but not cascading failure dynamics (where one cell failure triggers another). Real networks exhibit non-linear cascades. *Threats to Validity #5.*

**Limitation 7: 100-cell latency exceeds the O-RAN budget.**
10.25 ms > 10 ms. 6G compliance is demonstrated at 12-cell and 36-cell only. Explicitly stated in Section IV-D.

### 6.3 The Fundamental Design Tradeoff

CASTER-ZT makes an explicit, principled tradeoff:

**Maximum precision (0% false hard-blocks) at the cost of imperfect recall (74.2% detection).**

The paper argues this is correct for disaster recovery: a false block delays restoring communication and may cost lives directly. A missed rogue detection allows some harm, but scope-reduction mitigates the damage from partially-detected rogues. This is a **domain-specific value judgment** — not a universal engineering truth. In financial fraud detection, higher recall at the cost of more false positives would be the right tradeoff.

### 6.4 The Comparison Is Fair But Imperfect

**What is fair:**
- All methods use the same simulated environment, same random seeds, same attack conditions.
- Statistical tests account for multiple comparisons (Holm-Bonferroni).

**What is potentially unfair:**
- Baselines were adapted to this specific setting. Original-author tuning might improve their results.
- CASTER-ZT was designed specifically for this setting — home-field advantage.

The correct interpretation: "In this disaster-recovery setting with these adaptations, CASTER-ZT achieves zero false hard-blocks while maintaining 74.2%+ detection — something no evaluated method achieves simultaneously." This is a valid contribution. It is NOT a claim that CASTER-ZT is universally superior to all shielding methods.

---

<a id="step-7-conclusion"></a>
## STEP 7 — Conclusion

*What was built, what was proven, what remains to be done.*

---

### 7.1 What Was Built

CASTER-ZT is a decision-control framework for autonomous network recovery in disaster scenarios. Two deliberately separated layers:

**Learned intelligence layer (~20K parameters):**
- GNN encoder: reads network graph → 64-dim contextual cell embeddings
- Policy head: proposes the best recovery action (trained by imitation)
- Trust autoencoder: evaluates telemetry integrity + action consistency → trust score tau
- Risk scorer: evaluates action danger independent of identity → risk score rho
- Contrastive encoder: measures benign/adversarial interpretation divergence → Delta
- MC-Dropout: estimates the AI model's own uncertainty → u

**Deterministic safety layer (14 scalar parameters):**
- Authorization gate: checks identity credentials → alpha ∈ {0,1}
- Deterministic shield: combines (tau, rho, u, Delta, alpha) → exactly one of five decisions

The deliberate separation of learned intelligence from deterministic safety is the paper's core architectural contribution.

### 7.2 What Was Proven (Evidence Sources)

**Empirically proven** (2,420-run campaign, Wilcoxon + Holm-Bonferroni statistical testing):
- 74.2%–98.3% rogue detection (scales with topology size)
- Zero false hard-blocks across all conditions and threshold values
- omega_rec = 0.733 under attack vs. 0.201 for unshielded baseline (p < 0.001)
- 3.07 ms per-decision latency at 12-cell (within 10 ms O-RAN budget)
- ~80 KB model memory

**Theoretically proven** (10 propositions with mathematical proofs in supplemental material):

| # | Name | What it guarantees |
|---|------|-------------------|
| 1 | Monotone conservatism | Worse inputs → stricter output, always |
| 2 | Unauthorized exclusion | alpha=0 → BLOCK, no exceptions |
| 3 | Divergence safeguard | Extreme Delta → BLOCK |
| 4 | Decision completeness | Every input → exactly one output |
| 5 | Complexity bound | O(L·\|E\|·d + \|A\|·k) per decision |
| 6 | Defense-in-depth | Combined attack Pr[ALLOW] ≤ ε_α × ε_τ |
| 7 | Calibration-consistent accuracy | Hoeffding bound on empirical false-allow rate |
| 8 | Conformal coverage | Distribution-free false-allow rate ≤ α |
| 9 | Calibration convergence | Threshold → optimal at O(1/√n) |
| 10 | Scope limitations | Explicit non-claims (no global optimality, no universal defense) |

### 7.3 What Remains to Be Done

Future work stated explicitly in the paper:
1. Adversarial training of the trust autoencoder (improve telemetry-poisoning detection)
2. RL-based policy optimization (replace imitation learning with reward-based learning)
3. Cross-source GNN consistency (use multiple telemetry streams for stronger poisoning detection)
4. Evaluation under adaptive adversaries (adversary knows and adapts to thresholds)
5. Inference optimization for 100-cell deployment (quantization, graph sparsification to meet 10 ms budget)

### 7.4 The Bigger Picture

CASTER-ZT is a proof-of-concept that a useful, deployable autonomous AI system for critical infrastructure can simultaneously be:
- **Small** enough for edge deployment (~80 KB, ~20K params)
- **Fast** enough for real-time operation (3.07 ms)
- **Backed** by formal mathematical guarantees (10 propositions)
- **Transparent** enough for regulatory compliance (deterministic, auditable shield)

This is NOT a claim of production-readiness — the simulation-only evaluation, limited adversary model, and telemetry-poisoning gap are real. But the design pattern — **learned intelligence + deterministic shield + formal guarantees** — is a demonstrated viable architecture for this class of problem.

---

<a id="appendix-a-the-ten-propositions-deep-dive"></a>
## APPENDIX A — The Ten Propositions: Deep Walkthrough

> *Section 7.2 listed the ten propositions as one-line summaries. This appendix goes deeper: for each proposition, you get the formal statement, why it matters in practice, and the proof intuition (the mathematical reasoning behind it). You do NOT need to read Appendix A to understand the system — but if you want to understand WHY the guarantees hold, this is where you go.*

---

### Proposition 1: Monotone Shield Conservatism

**Statement:** Decreasing trust (tau) or increasing risk (rho), uncertainty (u), or divergence (Delta) cannot move the shield's output to a less conservative decision.

**Why it matters:** The shield is predictable under degradation. No adversary can manufacture a "worse but safer-looking" input that loosens the shield's response.

**Proof intuition:** `g_t = 0.25*(1−tau) + 0.25*rho + 0.25*u + 0.25*Delta` is monotonically increasing in (1−tau), rho, u, Delta — since all coefficients are positive, increasing any threat signal increases g_t. Since thresholds are strictly ordered (0.30 < 0.50 < 0.70 < 0.90), a higher g_t can only move to a stricter threshold region. Simultaneously, tau_min = 0.50 + 0.10*rho + 0.15*u increases with rho and u, making ALLOW harder. Both effects reinforce each other. Formally: for any component x ∈ {1−tau, rho, u, Delta}, dg_t/dx = 0.25 > 0. QED by monotonicity of g_t and the decision rule. *Evidence: Supplemental Proof 1.*

---

### Proposition 2: Unauthorized-Actuation Exclusion

**Statement:** If alpha = 0, then d = BLOCK.

**Why it matters:** No unauthorized entity can ever receive ALLOW, regardless of how benign its action looks — even if tau=1, rho=0, u=0, Delta=0. The authorization gate is an absolute firewall.

**Proof:** The decision rule evaluates Rule 1 (alpha = 0 → BLOCK) before any permissive branch. Since the rule tree uses strict priority (first match terminates), Rule 1 terminates the evaluation immediately when alpha=0. *Evidence: Supplemental Proof 2.*

---

### Proposition 3: Divergence-Triggered Safeguard

**Statement:** Delta > delta_max_hard (1.00) → BLOCK. Delta > delta_max (0.50) → not ALLOW.

**Why it matters:** Extreme divergence between benign and adversarial interpretations triggers automatic safety response, regardless of other signal values.

**Proof:** Rule 2 checks Delta > 1.00 before any permissive branch. For the ALLOW branch (Rule 3), the condition explicitly requires Delta ≤ 0.50. If Delta ∈ (0.50, 1.00], Rule 3 fails (not ALLOW), and the decision falls to Rules 4–7 based on g_t. If Delta > 1.00, Rule 2 catches it first. *Evidence: Supplemental Proof 3.*

---

### Proposition 4: Bounded Decision Completeness

**Statement:** Every valid input (tau, rho, u, Delta, alpha) ∈ [0,1]⁴ × {0,1} maps to exactly one decision in D. The shield is a total function — no input is left unhandled.

**Why it matters:** No undefined behavior. No crashes. No situations where the shield "doesn't know" what to do. Every possible input is handled.

**Proof:** The 7-rule decision tree is exhaustive. Rule 7 (g_t ≥ 0.90) catches ALL remaining cases (since if Rules 1–6 all fail, g_t must be ≥ 0.90). Threshold ordering ensures mutual exclusivity: each rule covers a non-overlapping range of g_t. The use of non-strict lower bounds and strict upper bounds (e.g., [0.30, 0.50)) ensures boundary points belong to exactly one region. *Evidence: Supplemental Proof 4.*

---

### Proposition 5: Per-Decision Complexity Bound

**Statement:** Total per-decision complexity is O(L·|E|·d + |A|·k).

**Why it matters:** Computation time is predictable and bounded — essential for meeting the 10 ms O-RAN real-time budget.

**Breakdown:**
- GNN (L=2 layers, |E| edges, d=64 dims): 2 passes over all edges, each doing d-dimensional arithmetic → O(L·|E|·d)
- Risk Scorer + Contrastive (|A|=6 actions, k=32 dims): scoring 6 candidates → O(|A|·k)
- Shield evaluation: O(1) — 7 arithmetic comparisons

For 12-cell topology: L=2, |E|≈30, d=64, |A|=6, k=32 → 2×30×64 + 6×32 = 3,840 + 192 = 4,032 elementary operations per decision cycle.

*Evidence: Supplemental Proof 5.*

---

### Proposition 6: Defense-in-Depth Bound ⭐ *Most Important*

**Statement:** Let ε_α = false-negative rate of the authorization gate (probability it misses an attack), ε_τ = false-negative rate of the trust-risk gate. Under combined attack with conditionally independent gates: Pr[ALLOW | combined attack] ≤ ε_α × ε_τ.

**Why it matters:** This is the mathematical foundation of *layered security*. If each gate has a 10% failure rate independently, the combined failure probability is 1% — not 10% + 10% = 20%. The two-gate system provides *multiplicative*, not additive, security improvement. This is the quantitative argument for why CASTER-ZT is more than the sum of its parts.

**Concrete example:**
```
If ε_α = 0.05 (auth gate misses 5% of identity attacks)
   ε_τ = 0.10 (trust gate misses 10% of telemetry attacks)

Then: Pr[ALLOW | combined attack] ≤ 0.05 × 0.10 = 0.005 = 0.5%
(NOT 0.05 + 0.10 = 15%)
```

**Proof intuition:**
```
Pr[ALLOW | combined] 
= Pr[alpha=1 | id-attack] × Pr[g < gamma1 | telem-attack]
≤ ε_α × ε_τ
```
The factorization holds because the authorization gate uses credential verification (a separate database check) while the trust-risk gate uses telemetry reconstruction error (a completely different signal source). A telemetry poisoning attack cannot affect the credential database; a stolen credential cannot change the autoencoder's reconstruction error. Hence the two events are conditionally independent. *Evidence: Supplemental Proof 6.*

---

### Proposition 7: Calibration-Consistent Accuracy

**Statement:** For empirical false-allow rate ε̂ on n i.i.d. calibration episodes: Pr[ε* ≤ ε̂ + √(ln(1/δ)/(2n))] ≥ 1−δ.

**Why it matters:** This gives you a statistical guarantee on how well the empirical false-allow rate estimates the true false-allow rate. With n=1000 calibration episodes and δ=0.01: the true rate ε* is at most ε̂ + 0.048 with 99% confidence.

**Proof:** By Hoeffding's inequality for bounded random variables: each calibration episode produces a Bernoulli outcome (allow on unsafe action: yes/no). Pr[ε* − ε̂ > t] ≤ exp(−2nt²). Setting t = √(ln(1/δ)/(2n)) gives the result. *Evidence: Supplemental Proof 7.*

---

### Proposition 8: Conformal Admissibility Coverage ⭐ *Distribution-Free*

**Statement:** With gamma_1 set as the (1−α)-quantile of calibration nonconformity scores and exchangeable test episodes: Pr[unsafe action is not ALLOW-ed] ≥ 1−α.

**Why it matters:** This is the *strongest* guarantee in the paper. Unlike Proposition 7 (requires i.i.d., asymptotic), Proposition 8 requires only *exchangeability* (much weaker) and is an *exact finite-sample* guarantee. No matter what distribution the data comes from, as long as the calibration and test episodes are exchangeable, the false-allow rate is bounded by α. This is what makes CASTER-ZT's safety claims distribution-free.

**In plain language:** If you randomly shuffle all your episodes (calibration + test), and you can't tell which came first, then: the probability that a truly unsafe action gets ALLOWed is at most α — period.

**Practical example:** With α = 0.01 and n = 500 calibration episodes: at most 1% of truly unsafe actions will be falsely ALLOWed, with finite-sample certainty, without assuming anything about the data distribution.

**Proof reference:** By the conformal prediction framework (Angelopoulos and Bates, 2023): the empirical (1−α) quantile of calibration scores upper-bounds the (1−α) quantile of the test distribution under exchangeability. The shield ALLOWs only when g_t < gamma_1; gamma_1 is set as this quantile. *Evidence: Supplemental Proof 8.*

---

### Proposition 9: Calibration Convergence Rate

**Statement:** Under strictly increasing ε(gamma) with ε'(gamma) ≥ c_ε > 0: |gamma_1^(n) − gamma_1*| = O_P(1/√n).

**Why it matters:** The calibrated threshold gamma_1 converges to its optimal value at rate 1/√n. Doubling the calibration dataset cuts the calibration error by √2. This tells you how much calibration data you need.

**Proof sketch:** 
1. By Hoeffding: |ε̂(gamma) − ε(gamma)| ≤ √(ln(2/δ)/(2n)) with high probability.
2. By the mean value theorem: since ε'(gamma) ≥ c_ε, any error in ε̂ translates to at most (1/c_ε) times that error in gamma.
3. Combining: |gamma_1^(n) − gamma_1*| = O_P(1/√n).

*Evidence: Supplemental Proof 9.*

---

### Proposition 10: Scope Limitations (Explicit Non-Claims)

The paper explicitly does NOT claim:
- Global optimality of the recovery policy
- Universal robustness against all adversaries (especially adaptive ones who learn thresholds)
- Convergence of all neural components to global optima (training guarantees are local)
- That 74.2% detection generalizes to all attack types, topologies, or distributions
- Real-world validation beyond calibrated simulation

**Why state this as a proposition?** Scientific integrity. Reviewers and readers will over-generalize results if the paper does not explicitly bound its claims. This proposition is the paper's formal self-limiting statement — "here is what we prove, and here is the boundary of that proof."

---

<a id="appendix-b-expert-qa"></a>
## APPENDIX B — Expert Questions and Answers

*Questions a professor, reviewer, or technical interviewer might ask. Every answer is grounded in what the paper actually proves.*

---

**Q: Why not use a real O-RAN testbed?**

A: Real disaster-monitoring testbeds with 6G infrastructure are not publicly available (as of 2025). The standard methodology uses calibrated simulation; SWaT and WADI are the field-standard testbed datasets for adversarial control system research. CASTER-ZT calibrates against four real datasets and validates telemetry distributions with K-S tests (p > 0.68). The shield's 10 theoretical guarantees hold regardless of data provenance — they are mathematical, not empirical. Live O-RAN evaluation is explicitly identified as critical future work (Section V).

---

**Q: Detection rate of only 74.2%. Why should anyone trust this system?**

A: Three points. First, 74.2% is at the smallest scale (12-cell) — at realistic deployment scales (100 cells), detection is 98.3%. Second, the missed 25.8% are sophisticated mimicry attacks — no other evaluated baseline detects these at a comparable precision level (Shield-Binary gets 88.3% but with 48.8% false hard-blocks, which is operationally worse). Third, CASTER-ZT achieves zero false hard-blocks across all conditions — every action it constrains is genuinely suspicious. The 74.2% is an explicit, principled operating point, not a system failure.

---

**Q: Is the conditional independence assumption in Proposition 6 realistic?**

A: The authorization gate uses a credential database (identity check); the trust-risk gate uses telemetry reconstruction error (anomaly detection). These sense completely different physical phenomena. A telemetry poisoning attack cannot modify the credential database. A stolen credential cannot change the autoencoder's reconstruction error on raw sensor data. The independence is physically grounded in the architecture. A threat model where the adversary simultaneously compromises the credential system AND the sensor network is a stronger attack than the paper assumes — stated as a scope limitation.

---

**Q: Why not use deep RL instead of imitation learning?**

A: Two reasons. First, RL requires a reward function for security decisions — what is the reward for blocking a rogue vs. false-blocking a legitimate action during a disaster? Misspecified rewards could cause the policy to learn to exploit the shield (rewarded for flagging everything as rogue → stop recovery entirely). Second, the shield's 10 propositions hold regardless of how the policy is trained — the guarantees are policy-agnostic. RL-based policy optimization is explicitly listed as future work.

---

**Q: The shield is just if-then-else logic. Where is the novelty?**

A: The novelty is in the combination, not any individual component. The if-then-else structure is deliberately simple because simplicity is what enables formal proof. The 10 propositions cannot be claimed by any single prior method. The inputs to the if-then-else come from a sophisticated learned architecture (GNN, trust autoencoder, contrastive encoder, risk scorer). The whole is: *complex learned inputs → simple provably-safe decision rule*. That combination is the contribution.

---

**Q: What about adversarial attacks on the GNN itself (graph-level perturbations)?**

A: The paper cites Zugner et al. (2018) and Dai et al. (2018) on adversarial attacks on GNNs. CASTER-ZT does NOT defend against graph-level adversarial perturbation of the network topology. However, Proposition 6 provides partial protection: even if the GNN is fooled and proposes a malicious action, the shield evaluates that action against independent trust, risk, divergence, and authorization signals. Fooling the GNN alone is insufficient to bypass the shield — the adversary must simultaneously fool all five signal channels. GNN adversarial robustness is identified as future work.

---

**Q: Why equal weights (0.25 each) in the conservatism score?**

A: Equal weights are the simplest, most unbiased starting point when you have four signals of roughly similar importance and no domain theory to prioritize one. The ablation confirms trust is the most important component — but the threshold sensitivity analysis shows the system is robust across gamma_1 ∈ [0.10, 0.60]. Performance is dominated by the trust assessment quality, not by the 0.25 vs. 0.30 weight difference. Principled weight optimization (e.g., via multi-objective calibration) is future work.

---

**Q: What if the adversary learns the exact shield thresholds?**

A: The threat model assumes gray-box (architecture known, thresholds unknown). If thresholds were known, the adversary could craft inputs just below each boundary — valid concern. Proposition 6 still provides partial protection: even with known thresholds, the adversary must simultaneously keep tau above tau_min (hard without clean telemetry), keep g_t below 0.30 (hard with high-risk rogue action), AND have valid credentials (hard to obtain). Single-dimension attacks are insufficient. The paper mentions periodic recalibration as a mitigation for threshold leakage.

---

**Q: Why autoencoder for anomaly detection instead of a supervised binary classifier?**

A: Two structural reasons. First, a supervised classifier can only detect attack types seen during training. The autoencoder detects ANY input that deviates from the normal manifold — including novel attack types. Second, the autoencoder produces the reconstruction residual `delta_hat = x_t - AE(x_t)`, which is used directly to construct the adversarial hypothesis for the contrastive encoder. A supervised classifier produces only a score, not a residual — eliminating the divergence signal Delta_t entirely (as demonstrated by the IF-Trust ablation where Delta_t = 0).

---

**Q: How does this compare to LLM-based network controllers?**

A: Complementary architectures, not competing ones. LLM-based controllers provide intent decomposition, multi-step reasoning, and adaptive strategy — capabilities CASTER-ZT does not have. CASTER-ZT provides formal admissibility boundaries — capabilities no LLM controller has proven. Integration: LLM proposes an action; CASTER-ZT's shield evaluates and enforces it. The shield is policy-agnostic by design — it works with any proposer, including LLMs.

---

<a id="appendix-c-quick-reference-cheat-sheets"></a>
## APPENDIX C — Quick-Reference Cheat Sheets

---

### Cheat Sheet 1: Architecture at a Glance

```
+------------------------------------------------------------------+
| Component              | Params  | Input         → Output       |
|------------------------|---------|------------------------------|
| GNN Encoder            |  4,544  | Network graph → 64-dim emb.  |
| Policy Head            |  8,515  | Embeddings    → action probs |
| Trust Autoencoder      |  1,839  | Telemetry     → trust tau    |
| Risk Scorer            |  1,473  | Action+state  → risk rho     |
| Contrastive Encoder    |  3,648  | Telemetry pair→ divergence D |
| MC-Dropout (inference) |    —    | 20 passes     → uncertainty u|
| Authorization (det.)   |    —    | Identity token→ alpha {0,1}  |
|------------------------|---------|------------------------------|
| TOTAL LEARNED          | 20,019  |           (~80 KB)           |
| Shield (deterministic) |     14  | (tau,rho,u,D,alpha) → d_t   |
+------------------------------------------------------------------+

14 shield parameters: gamma_1=0.30, gamma_2=0.50, gamma_3=0.70,
  gamma_4=0.90, delta_max=0.50, delta_max_hard=1.00,
  w_1=w_2=w_3=w_4=0.25, c_rho=0.10, c_u=0.15, base_tau=0.50,
  e_thresh=0.5914
```

---

### Cheat Sheet 2: The Shield Decision Rule

```
Given: tau (trust), rho (risk), u (uncertainty), Delta (divergence), alpha (auth)

Compute:
  g       = 0.25*(1-tau) + 0.25*rho + 0.25*u + 0.25*Delta
  tau_min = 0.50 + 0.10*rho + 0.15*u

Decide (first matching rule wins):
  1. alpha = 0                               → BLOCK
  2. Delta > 1.00                            → BLOCK
  3. tau ≥ tau_min AND g < 0.30
     AND Delta ≤ 0.50                        → ALLOW
  4. g in [0.30, 0.50)                       → SCOPE-REDUCE
  5. g in [0.50, 0.70)                       → DEFER
  6. g in [0.70, 0.90) OR u > 0.80          → ESCALATE
  7. g ≥ 0.90                               → BLOCK  (also catches g > 1.0)
```

---

### Cheat Sheet 3: Key Results Comparison (Identity Abuse HIGH, 12-cell)

```
Method          | RogueDet | FalseBlk | omega_rec | Clean behavior
----------------|----------|----------|-----------|-------------------
CASTER-ZT       |  74.2%   |   0.0%   |   0.733   | ~10% scope-red
IF-Trust        | 100.0%   |   0.0%   |   0.925   | 100% scope-red (!)
Shield-Binary   |  88.3%   |  48.8%   |   0.758   | Many false BLOCK
Agentic-Auto    |  10.5%   |  56.8%   |   0.144   | Many false DEFER
CPO-Soft        |   0.0%   |   0.0%   |   0.201   | No detection

FalseBlk = fraction of hard BLOCK decisions on legitimate actions.
IF-Trust's 0% FalseBlk is because it SCOPE-REDUCES everything (never hard-blocks),
but that means 100% of clean actions are also constrained.
```

---

### Cheat Sheet 4: The Ten Propositions at a Glance

```
 1. Monotone conservatism       — worse inputs → stricter output, always
 2. Unauthorized exclusion      — alpha=0 means BLOCK, no exceptions
 3. Divergence safeguard        — Delta>1.00 → BLOCK; Delta>0.50 → not ALLOW
 4. Decision completeness       — every input → exactly one output
 5. Complexity bound            — O(L·|E|·d + |A|·k) per decision
 6. Defense-in-depth      [★]  — Pr[unsafe ALLOW] ≤ ε_α × ε_τ (multiplicative!)
 7. Calibration accuracy        — Hoeffding bound on empirical false-allow rate
 8. Conformal coverage    [★]  — distribution-free false-allow ≤ α
 9. Calibration convergence     — threshold → optimal at O(1/√n)
10. Scope limitations           — explicit non-claims (no global optimality, etc.)

[★] = most important propositions
```

---

### Cheat Sheet 5: The Five Decision Outcomes

```
ALLOW         Execute as proposed.
              Requires: authorized (alpha=1), high trust (tau ≥ tau_min),
                        low composite threat (g < 0.30), low divergence (Delta ≤ 0.50).

SCOPE-REDUCE  Execute with narrowed scope (fewer target cells, lower intensity).
              Triggers when: 0.30 ≤ g < 0.50

DEFER         Do NOT execute now. Wait for more information.
              Triggers when: 0.50 ≤ g < 0.70

ESCALATE      Flag for human operator review.
              Triggers when: 0.70 ≤ g < 0.90 OR u > 0.80

BLOCK         Reject the action entirely.
              Triggers when: alpha=0, OR Delta>1.00, OR g ≥ 0.90
```

---

### Cheat Sheet 6: Training Configuration

```
Component         | Loss            | LR      | Converges by | Key metric
------------------|-----------------|---------|--------------|------------------
Trust AE          | MSE (recon.)    | 5×10⁻⁴  | Epoch 16     | F1=0.580 (standalone)
Risk Scorer       | BCE             | 1×10⁻³  | Epoch 27     | AUC=0.999
Contrastive Enc.  | Margin (m=1.0)  | 1×10⁻³  | Epoch 44     | Margin loss → 0
GNN + Policy      | Cross-entropy   | 1×10⁻³  | Epoch 17     | Accuracy=1.000
Shield            | N/A (calibrate) |  N/A    | < 1 second   | Conformal bound

All components: Adam optimizer, p=0.10 dropout during training
Inference: MC-Dropout ON, T=20 passes
Data: 2,000 episodes × ~30 ticks ≈ 60,000 decision steps
Split: 70% train / 15% validation / 15% test (stratified by attack condition)
```

---

### Cheat Sheet 7: Real Data Sources

| Dataset | What it is | How it is used |
|---------|-----------|----------------|
| Intel Lab (2004) | Sensor readings from 54 sensors in a lab building | Calibrates sensor failure dynamics |
| SensorScope (2008) | Alpine environmental sensor network | Calibrates 40% simultaneous failure fraction |
| SWaT (2017) | Industrial control system testbed (water treatment) | Calibrates medium-severity adversarial injection parameters |
| WADI (2018) | Water distribution testbed (larger scale) | Calibrates high-severity adversarial injection parameters |
| Narayanan et al. 2021 | Commercial 5G throughput traces | Fits LogNormal(4.50, 0.80) for throughput |
| Xu et al. 2020 | Operational 5G latency measurements | Fits Gamma(2.5, 4.0) + 5ms for latency |
| 3GPP TR 38.913 | NR specification | Fits Beta(0.5, 50) for packet loss |
| Xu et al. 2017 | Urban mobile traffic patterns | Fits Beta(2.0, 3.0) for cell load |

---

### Cheat Sheet 8: CASTER-ZT Acronym

| Letter | Stands for | What it means |
|--------|-----------|---------------|
| **C** | Causal | Dual-hypothesis evaluation (benign + adversarial view simultaneously) |
| **A** | Autonomous | Operates at the edge without human intervention per-decision |
| **S** | Shielded | Every action passes through the deterministic safety shield |
| **T** | Telemetry-aware | Trust autoencoder evaluates telemetry integrity every cycle |
| **E** | Event-aware | Uses full disaster context (cell states, recovery progress) |
| **R** | Recovery | Designed specifically for disaster recovery network scenarios |
| **Z** | Zero (Trust) | No entity is implicitly trusted; continuous verification |
| **T** | Trust | Every action is re-verified, not just at login time |

---

*End of CASTER-ZT Deep Explainer.*
*Every claim in this document traces back to the paper or its cited sources.*
*If a section is still unclear, re-read it with Step 1 (Vocabulary) open alongside.*
*Found an error or unclear passage? The document is versioned — report it with the specific section.*

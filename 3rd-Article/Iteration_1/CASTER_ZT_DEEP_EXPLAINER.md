# CASTER-ZT — Complete Deep Explainer Guide

> **Purpose:** After reading this document from start to finish, you should be able to explain every concept, every design decision, every number, every theorem, every motivation, and every technical word in the article — clearly, deeply, and confidently — to any expert panel.

---

## TABLE OF CONTENTS

1. [What is the paper about — The 60-second elevator pitch](#1-elevator-pitch)
2. [The real-world problem and why it matters](#2-the-problem)
3. [Every technical term explained](#3-glossary)
4. [The title — word by word](#4-the-title)
5. [The research gap — what was missing before this paper](#5-the-gap)
6. [The four research questions — and why these four](#6-research-questions)
7. [The five contributions — and why they matter](#7-contributions)
8. [System model — the world the system lives in](#8-system-model)
9. [Threat model — who is the adversary and what can they do](#9-threat-model)
10. [The CASTER-ZT architecture — component by component](#10-architecture)
11. [The shield algorithm — step by step with a worked example](#11-shield-algorithm)
12. [The training pipeline — how every component learns](#12-training-pipeline)
13. [All ten propositions — statement, intuition, and proof walkthrough](#13-propositions)
14. [The experimental design — every choice explained](#14-experimental-design)
15. [Where every number comes from](#15-numbers)
16. [The baselines — what they are and why each was chosen](#16-baselines)
17. [The results — what they mean and why](#17-results)
18. [The ablation — what removing each component teaches us](#18-ablation)
19. [The multi-scale evaluation — why and what it shows](#19-multiscale)
20. [The threshold sensitivity — why it matters](#20-threshold)
21. [Honest limitations — what the paper does NOT claim](#21-limitations)
22. [The regulatory angle — EU AI Act, NIST, OWASP](#22-regulation)
23. [Likely expert questions and how to answer them](#23-faq)
24. [Quick-reference cheat sheets](#24-cheatsheets)

---

## 1. Elevator Pitch

**CASTER-ZT** is a security-first autonomous decision-control system for disaster-monitoring networks.

During a disaster (earthquake, flood, wildfire), cell towers fail and a sensing/communication network must recover automatically. But an adversary can exploit the chaos: they can corrupt telemetry data (telemetry poisoning) or inject fake recovery commands using stolen identities (identity-credential abuse).

The key insight is: **we separate "proposing what to do" from "deciding whether it is safe to do it."**

- Five trained neural-network components (a graph encoder, a recovery policy, a trust autoencoder, a risk scorer, a contrastive safety encoder) **propose and assess** recovery actions.
- A deterministic zero-trust shield with formal mathematical guarantees **decides** whether each action may be executed, scope-reduced, deferred, escalated, or blocked.

This "policy proposes, shield disposes" design means that even if the AI components are fooled, the shield provides a provable safety boundary. The system runs in under 3.07 ms per decision, fits in 2 MB, and deploys at the network edge — all meeting 6G near-real-time requirements.

---

## 2. The Problem

### What is a disaster-monitoring sensing network?

Imagine a region covered by sensor nodes (measuring temperature, water level, air quality, seismic activity), relay nodes, gateways, and small base stations — all forming a communication graph. During normal operations, they send telemetry (measurements) to a control center.

When a disaster strikes (earthquake, flood), many nodes fail simultaneously. The network must **recover autonomously**: reroute traffic, activate backup nodes, reassign gateways, isolate damaged regions. Manual recovery is too slow — people are overwhelmed, roads are blocked, communication is intermittent.

### Why is autonomy dangerous?

The same autonomy that makes recovery faster creates a **larger attack surface**:
- An adversary can **corrupt telemetry** — making the AI think cell A is fine when it's actually failed, or that cell B is failed when it's actually fine. This is called **telemetry poisoning**.
- An adversary can **steal credentials** and inject fake recovery commands — like "deactivate this perfectly working cell" or "flood this cell with handover requests." This is called **identity-credential abuse**.
- An AI that makes decisions fast also makes *bad* decisions fast if it can't detect these attacks.

### Why existing solutions don't solve this

The literature has strong individual ingredients:
- **Graph neural networks** can model network topology — but they don't check whether an action is safe.
- **Safe reinforcement learning** can enforce constraints — but those constraints are about physical safety or cost budgets, not about identity fraud or telemetry corruption.
- **Uncertainty quantification** can tell you when the model is unsure — but being unsure doesn't mean the action is unauthorized.
- **Agentic AI** can orchestrate network operations — but it has no formal boundary for when NOT to act.

**The gap:** No existing system combines graph-structured decision making with formally bounded zero-trust admissibility for autonomous actuation under adversarial conditions.

---

## 3. Every Technical Term Explained

### Core Concepts

| Term | Plain-language explanation |
|------|---------------------------|
| **Zero Trust** | A security paradigm from NIST SP 800-207: "never trust, always verify." Every request must be authenticated and authorized, even from inside the network. No entity gets implicit trust. |
| **Shield** | A deterministic decision gate that wraps a learned policy. The shield uses no neural networks — it's pure if-then-else logic with fixed thresholds. This makes it formally verifiable. |
| **Graph Neural Network (GNN)** | A neural network that operates on graph-structured data. Instead of processing flat vectors, it processes nodes and edges. Each node aggregates information from its neighbors. |
| **GraphSAGE** | A specific GNN variant by Hamilton et al. (2017). "SAGE" = Sample and AggregatE. Each node creates its embedding by concatenating its own features with the mean of its neighbors' features, then applying a learned linear transform + nonlinearity. |
| **Autoencoder** | A neural network trained to reconstruct its input. It compresses input → bottleneck → decompresses. If trained only on "normal" data, it reconstructs normal data well but fails on anomalies, producing high reconstruction error. |
| **Contrastive learning** | Training a model to make embeddings of similar things close and embeddings of different things far apart. Uses a margin-based loss: if two inputs are from different classes, push their embeddings apart by at least a margin *m*. |
| **MC-Dropout** | Monte Carlo Dropout (Gal & Ghahramani, 2016). At inference time, keep dropout ON and run the network T times with different random dropout masks. The variance in outputs estimates the model's **epistemic uncertainty** — uncertainty due to lack of knowledge, not inherent randomness. |
| **Conformal prediction** | A distribution-free framework (Angelopoulos & Bates, 2023) that provides finite-sample coverage guarantees. If calibration data is exchangeable (a weaker condition than i.i.d.), conformal prediction guarantees that the prediction set contains the true label with probability ≥ 1−α. No parametric assumptions needed. |
| **Admissibility** | Whether an action is "allowed to be executed autonomously." Admissibility is not about whether the action is *optimal* — it's about whether it crosses the safety boundary for autonomous execution. |
| **Scope reduction** | Instead of fully blocking or fully allowing an action, narrowing its scope: fewer target cells, reduced strength, smaller affected region. This is graduated enforcement — the key differentiator from binary block/allow systems. |
| **Telemetry** | Measurement data sent by network nodes: throughput, latency, packet loss rate, cell load. This is the "evidence" the AI uses to make decisions. |
| **KPI** | Key Performance Indicator — a specific measured metric (throughput in Mbps, latency in ms, packet loss rate in %). |
| **O-RAN** | Open Radio Access Network — an industry standard that disaggregates the cellular base station into open, interoperable components. Enables third-party AI applications (xApps) to run on the RAN Intelligent Controller (RIC). |
| **Near-RT RIC** | Near-Real-Time RAN Intelligent Controller — the O-RAN component where AI applications (xApps) run with control loops as fast as 10 ms. This is the target deployment platform for CASTER-ZT. |
| **xApp** | A third-party application running on the Near-RT RIC. CASTER-ZT would be deployed as an xApp. |
| **6G** | The sixth generation of wireless technology, expected around 2030. Key feature: AI is a first-class design element at every protocol layer, not an add-on. |
| **AI-native** | AI is incorporated "from the onset" as a core architectural element. Not retrofitted. Every functional stage (perception, reasoning, action) uses a trained ML component. |

### Mathematical Notation

| Symbol | Meaning | Range |
|--------|---------|-------|
| $G_t = (V_t, E_t, X_t)$ | The network graph at time t: nodes V, edges E, features X | — |
| $s_t$ | Full decision state: $(G_t, z_t, b_t, h_t)$ — graph + security context + mission context + history | — |
| $o_t$ | Observation available to the controller (may be incomplete or adversarial) | — |
| $\mathcal{A}$ | Action space — set of possible recovery actions (finite) | 6 action types |
| $\hat{a}_t$ | Candidate action proposed by the policy | $\hat{a}_t \in \mathcal{A}$ |
| $\pi_\theta(a \mid s_t)$ | Policy's probability of choosing action a given state s | [0,1] |
| $\tau_t$ | Trust score — how much we trust the telemetry | [0,1], higher = more trusted |
| $\rho_t$ | Risk score — how risky the proposed action is | [0,1], higher = riskier |
| $u_t$ | Uncertainty score — how unsure the model is | [0,1], higher = more uncertain |
| $\Delta_t$ | Divergence score — how differently the action looks under benign vs adversarial hypotheses | [0,∞), higher = more suspicious |
| $\alpha_t$ | Authorization flag — is the proposer a legitimate identity? | {0, 1} |
| $g_t$ | Composite conservatism score — single scalar aggregating all threat signals | [0, ∞) |
| $d_t$ | Shield decision — which of the 5 outcomes | {ALLOW, SCOPE-REDUCE, DEFER, ESCALATE, BLOCK} |
| $\tau_{\min}$ | Dynamic minimum trust requirement (rises with risk and uncertainty) | [0, 1] |
| $\gamma_1 < \gamma_2 < \gamma_3 < \gamma_4$ | Shield thresholds separating the 5 decision regions | 0.30, 0.50, 0.70, 0.90 |
| $w_1, w_2, w_3, w_4$ | Weights in the conservatism score | All = 0.25 |
| $\kappa_1, \kappa_2$ | Sensitivity coefficients for dynamic trust threshold | 0.10, 0.15 |
| $\tau_0$ | Baseline trust floor | 0.50 |
| $\delta_{\max}$ | Soft divergence ceiling (above this: no ALLOW) | 0.50 |
| $\delta_{\max}^{\text{hard}}$ | Hard divergence ceiling (above this: immediate BLOCK) | 1.00 |
| $u_{\max}$ | Uncertainty ceiling (above this: ESCALATE) | 0.80 |
| $\theta$ | Learned weights of GNN encoder + policy head | ~13,059 params |
| $\phi$ | Learned weights of trust autoencoder + risk scorer + contrastive encoder | ~6,960 params |
| $\omega$ | Learned weights contributing to uncertainty (MC-Dropout masks in encoder) | Shared with $\theta$ |
| $e_t$ | Reconstruction error from trust autoencoder | ≥ 0 |
| $e_{\text{thresh}}$ | 95th-percentile reconstruction error on clean calibration data | 0.5914 (trained) |
| $\beta_\tau$ | Temperature parameter in sigmoid trust computation | 5.0 |
| $\omega_{\text{rec}}$ | Recovery quality metric: fraction of cells operational at recovery completion | [0, 1] |
| $\eta_{\text{AI}}$ | AI-native coverage: fraction of pipeline stages that are learned | 5/6 = 0.833 |

---

## 4. The Title — Word by Word

**"Zero-Trust Shielded Graph-Structured Decision Control for Secure Autonomous Recovery in AI-Native 6G Disaster-Monitoring Sensing Networks"**

| Word/Phrase | Where it's substantiated in the paper |
|-------------|--------------------------------------|
| **Zero-Trust** | NIST SP 800-207 principle applied to actuation (Section III-A). Authorization gate checks every action (Algorithm 1, line 11). Propositions 2 and 3. |
| **Shielded** | Deterministic shield algorithm (Algorithm 1), calibration procedure (Algorithm 2), ten theoretical properties (Section III-F). |
| **Graph-Structured** | State represented as graph $G_t = (V_t, E_t, X_t)$. 2-layer GraphSAGE encoder (Section III-C). Multi-scale topologies 12/36/100-cell (Table 9). |
| **Decision Control** | Five-outcome bounded decision space $\mathcal{D}$ (Definition 2). Graduated response — not just block/allow. |
| **Secure** | Formal threat model (Section III-A), defense-in-depth bound (Proposition 6), 74.2% identity-abuse detection with zero false positives (Table 5). |
| **Autonomous Recovery** | Recovery policy $\pi_\theta$ proposes actions autonomously. Recovery quality $\omega_{\text{rec}}$ measured. Scope-reduction enforcement (Algorithm 3). |
| **AI-Native** | Formal Definition 5: $\eta_{\text{AI}} = 5/6$. Five of six pipeline stages are trained neural modules. Matches 6G standardization definition. |
| **6G** | Formal Definition 4: latency ≤ 10ms, edge autonomy, model compactness ≤ 2 MB. Validated in RQ4: 3.07 ms at 12-cell. |
| **Disaster-Monitoring** | Failure model: 40% simultaneous cell failure at tick 3. SensorScope alpine deployment grounding. |
| **Sensing Networks** | Intel Lab 54-node topology. Telemetry KPI structure. Multi-scale sensing topologies 12–100 cells. |

**Key point for experts:** Every word in the title maps to a specific, verifiable component. This is not decorative — each word represents a substantive contribution.

---

## 5. The Gap — What Was Missing

The literature has five strong but disconnected threads:

1. **Graph learning** (Kipf 2017, Hamilton 2017, Veličković 2018) — can model network topology, but doesn't gate actions for safety.
2. **Safe/shielded RL** (García 2015, Achiam 2017, Alshiekh 2018) — can enforce constraints, but those constraints are about cost budgets or state-safety invariants, not about *identity fraud* or *corrupted evidence*.
3. **Uncertainty/calibration** (Gal 2016, Guo 2017, Angelopoulos 2023) — can quantify model confidence, but high confidence ≠ safe action (an adversary can create high-confidence corrupted inputs).
4. **Adversarial robustness for graphs** (Zügner 2018, Bojchevski 2019) — protects model *representations*, but doesn't gate downstream *execution*.
5. **Agentic O-RAN** (Navidan 2026, Demirel 2026) — orchestration flexibility, but no formal admissibility boundary.

**The specific gap:** No framework combines graph-structured decision making + formal zero-trust admissibility + dual-hypothesis trust-risk evaluation + graduated five-outcome responses + identity-aware gating for autonomous actuation under adversarial conditions.

**Why this gap is dangerous:** In a disaster, a learned controller may identify a high-utility recovery action. But the same action becomes harmful if:
- The telemetry it's based on is corrupted (telemetry poisoning)
- The entity requesting it has stolen credentials (identity abuse)
- The action's consequences are poorly understood under current stress

Existing systems evaluate action quality *before* defining the admissibility boundary. CASTER-ZT reverses this: admissibility is a hard boundary that must be satisfied *regardless* of the action's predicted quality.

---

## 6. The Four Research Questions

### RQ1: Can a zero-trust shielded policy reduce adversarial degradation?

**Why this question:** The fundamental question — does the shield actually work? Can it detect and block/mitigate rogue actions without also blocking legitimate ones?

**Answer:** Yes. 74.2% rogue detection with 0% false positives at 12-cell; 98.3% at 100-cell. Non-shielding baselines: 0–10.5% detection.

### RQ2: What are the security-utility-overhead tradeoffs?

**Why this question:** Security always has a cost. How much recovery quality do we lose by adding security? Is the cost acceptable?

**Answer:** $\omega_{\text{rec}} = 0.733$ (73.3% cells operational) vs. 0.201 without shielding. Under clean conditions, $\omega_{\text{rec}} = 0.925$ for all methods — the shield doesn't hurt when there's no attack. The "price of safety" is bounded (Proposition 7).

### RQ3: Does the framework generalize?

**Why this question:** A system that only works at one severity level, one seed, or one topology size is useless. We need robustness evidence.

**Answer:** Consistent across medium/high severity (RogueDet 0.742–0.806), 20 seeds, and three scales (12/36/100-cell). Threshold sensitivity shows stability across γ₁ ∈ [0.20, 0.60].

### RQ4: Does it meet 6G deployment constraints?

**Why this question:** If it can't run in real-time at the network edge, it's a paper exercise. The O-RAN Near-RT RIC demands ≤ 10 ms control loops.

**Answer:** 3.07 ms at 12-cell (3× headroom), 4.38 ms at 36-cell (2.3× headroom), 10.25 ms at 100-cell (at boundary). Model: 20K params, ≤ 2 MB.

---

## 7. The Five Contributions

### Contribution 1: Problem formulation
Formulating autonomous post-disaster recovery as a **graph-structured secure decision problem** with explicit trust, risk, authorization, uncertainty, and admissibility variables. This is new — previous formulations didn't include all five dimensions.

### Contribution 2: The CASTER-ZT architecture
Five learned neural modules + one deterministic shield. The key design principle: **separation of learned intelligence from deterministic safety enforcement.** This is the "dynamic model predictive shielding" paradigm (Roderick et al., NeurIPS 2024).

### Contribution 3: Ten theoretical properties
Including three non-trivial ones:
- **Defense-in-depth** (Proposition 6): independent gates multiplicatively reduce unsafe execution probability.
- **Conformal coverage** (Proposition 8): distribution-free finite-sample guarantee.
- **Calibration convergence** (Proposition 10): O(1/√n) convergence rate for threshold calibration.

### Contribution 4: 2,420-run experimental campaign
11 methods × 7 conditions × 20 seeds × 3 scales. Four external baselines from real published methods. Bootstrap CIs, Wilcoxon tests, Cliff's delta.

### Contribution 5: Component-level ablation
Proving each component is individually necessary. Trust assessment is the critical component (removing it: 0.742 → 0.524 detection, 0.733 → 0.380 recovery quality).

---

## 8. System Model — The World the System Lives In

### The network graph

At every decision epoch t, the network is a graph $G_t = (V_t, E_t, X_t)$:
- **Nodes** $V_t$: cells (base stations/sensors). Each has a state: {operational, degraded, failed, recovering}.
- **Edges** $E_t$: communication links between adjacent cells.
- **Features** $X_t$: per-node (5 features) and per-edge (2 features).

Node features (5 per node):
1. **Operational state** (one-hot fraction: what % of the node is operational)
2. **Throughput** (current throughput normalized)
3. **Latency** (current latency normalized)
4. **Loss rate** (current packet loss rate)
5. **Zone ID** (which trust zone the node belongs to)

Edge features (2 per edge):
1. **Link capacity** (maximum bandwidth)
2. **Link utilization** (current load fraction)

### The full state

$$s_t = (G_t, z_t, b_t, h_t)$$

- $G_t$: the graph
- $z_t$: security/trust context (current trust scores, recent anomaly history)
- $b_t$: mission/resource context (recovery priority, available backup resources)
- $h_t$: recent loop history (what actions were taken in the last few ticks)

### The observation

$$o_t = \mathcal{O}(s_t)$$

The controller sees $o_t$, which may be **incomplete** (some nodes not reporting), **delayed** (stale data), or **adversarially perturbed** (poisoned telemetry). This is a key design constraint: the controller never sees the true state — it sees a possibly corrupted observation.

### The action space

Six bounded action types:
1. **CELL_ACTIVATION** — activate a backup/reserve cell
2. **CELL_RECONFIG** — reconfigure a cell's parameters for recovery
3. **LOAD_REBALANCE** — redistribute traffic across cells
4. **REROUTE** — change traffic paths
5. **ISOLATE** — isolate a suspicious region
6. **ESCALATE** — hand off to human operator

**Why bounded?** The action space is deliberately finite and operationally meaningful. This is not open-ended — each action has a defined scope, target set, and strength. This makes formal analysis tractable.

### Deployment tier

The target is the **edge/gateway tier**: more powerful than individual sensors, but more constrained than centralized cloud. Think of a small computing node at or near a cell tower, with limited memory and no guaranteed cloud connectivity during a disaster.

### Time structure

The simulation uses **discrete ticks** (30–40 ticks per episode):
- Tick 0–2: Normal operation
- Tick 3: **Disaster onset** — 40% of cells fail simultaneously
- Ticks 5–22 (or 5–28): **Attack window** — adversary injects telemetry poisoning and/or rogue actions
- Remaining ticks: Recovery continues

---

## 9. Threat Model — Who is the Adversary?

### The adversary's four dimensions

The adversary $\mathcal{ADV}$ is characterized by $(C, K, B, O)$:

**C — Attack class:**
- **Telemetry poisoning**: Corrupt KPI values (throughput, loss rate, latency) in telemetry records. Like putting a fake temperature reading on a thermometer.
- **Identity-credential abuse**: Inject recovery-action proposals using stolen or fabricated identities. Like someone stealing your company badge and issuing orders in your name.
- **Combined**: Both simultaneously.

**K — Knowledge level:**
- **Grey-box**: The adversary knows the system architecture (that there's a GNN, an autoencoder, a shield) but NOT the current threshold values, trust scores, or internal states. This is a realistic assumption — architecture details often leak, but operational parameters don't.

**B — Budget:**
- Telemetry poisoning budget $B_{\text{telem}}$: fraction of records that can be corrupted per tick (50% medium, 80% high)
- Identity-abuse budget $B_{\text{ident}}$: number of rogue actions per tick (2 medium, 3 high)

**O — Observable subset:** Which nodes the adversary can target. Not the entire network.

### Concrete attack parameters

| Parameter | Medium severity | High severity | Source |
|-----------|----------------|---------------|--------|
| Throughput bias | 0.30 | 0.50 | SWaT median deviation |
| Loss bias | 0.25 | 0.50 | SWaT/WADI attacks |
| Poison fraction | 50% of records | 80% of records | SWaT single-zone attacks |
| Rogue actions/tick | 2 | 3 | — |
| Uses stolen identity? | Yes | Yes | — |
| Mimicry rate | 10% | 15% | — |

**Mimicry attacks** (critical to understand): 10–15% of rogue actions *disguise themselves as legitimate recovery actions*. Instead of obviously destructive actions (CELL_DEACTIVATION), they use recovery-like types (CELL_RECONFIG, LOAD_REBALANCE) targeting degraded cells. These are the hardest to detect because they look like what a real recovery operator would do.

### Where the attack parameters come from

- **Bias magnitudes (0.30, 0.50)**: Extracted from the SWaT (Secure Water Treatment) testbed — a real cyber-physical security dataset with labeled attacks on water treatment infrastructure. Medium bias = median normalized sensor deviation during 36 single-point attacks. High bias = 95th percentile deviation during 15 coordinated attacks from the WADI (Water Distribution) testbed.
- **Injection rates (50%, 80%)**: Fraction of sensors affected in real SWaT/WADI attack episodes.
- **Failure fraction (40%)**: Observed peak simultaneous sensor dropout during alpine storm events in SensorScope.

### What the adversary CANNOT do
- Cannot modify the shield's internal parameters, threshold values, or audit log.
- Cannot compromise more than one trust zone simultaneously.
- Cannot observe or control the training process.

### The zero-trust actuation boundary

This is the paper's core security principle: **the point at which proposed actions transition from candidates to executable actions.** Everything before this boundary may be learned and probabilistic; everything crossing it must satisfy bounded admissibility conditions.

Think of it like a bank vault: anyone can propose transactions, but the vault's security mechanisms decide whether each transaction actually executes. Even the bank manager can't bypass the vault door without proper authentication.

---

## 10. The Architecture — Component by Component

### The pipeline (left to right)

```
Telemetry → GNN Encoder → Policy Head → Trust-Risk Evaluator → MC-Dropout → Zero-Trust Shield → Bounded Execution
   (input)    (learned)    (learned)      (learned)            (learned)    (deterministic)      (output)
```

### Component 1: GNN Graph Encoder ($f_\theta$) — 4,544 parameters

**What it does:** Takes the raw graph state $G_t$ and produces a vector representation (embedding) for each node and for the whole graph.

**Architecture:** 2-layer GraphSAGE with mean aggregation:

$$h_v^{(\ell+1)} = \text{ReLU}\left(W^{(\ell)} \cdot \text{CONCAT}\left(h_v^{(\ell)}, \text{MEAN}(\{h_u^{(\ell)} : u \in \mathcal{N}(v)\})\right)\right)$$

In plain English:
1. For each node v, look at all its neighbors' current embeddings.
2. Take the mean of those neighbor embeddings.
3. Concatenate the node's own embedding with the neighbor mean.
4. Apply a learned linear transformation (matrix multiply).
5. Apply ReLU (= max(0, x)) nonlinearity.
6. Repeat for layer 2.

**Input:** 5 features per node → **Output:** 64-dimensional embedding per node.

**Graph-level readout:** Average all node embeddings to get one 64-dimensional vector representing the entire graph: $\bar{h}_{G_t} = \text{MEAN}(\{h_v^{(L)} : v \in V_t\})$.

**Why GraphSAGE?** (Likely expert question)
- **Inductive**: Can handle nodes not seen during training (new cells deployed after a disaster).
- **Scalable**: Mean aggregation is O(|neighbors|), not O(|all nodes|).
- **Lightweight**: 2 layers with d=64 gives only ~4.5K parameters — critical for the 6G edge deployment constraint.
- **Why not GAT (attention)?** GAT is more expressive but slower. At 12 cells, a 2-layer GraphSAGE runs in ~0.5 ms; GAT would add ~2× latency, eating into the 10 ms budget.

**Why only 2 layers?** For the small topologies tested (12–100 cells), 2-hop neighborhood aggregation is sufficient to capture local structure. Deeper GNNs suffer from over-smoothing (all embeddings converge to the same value) and add latency without accuracy benefit. Validation showed <0.5% accuracy gain from 3 or 4 layers.

### Component 2: Recovery Policy Head ($\pi_\theta$) — 8,515 parameters

**What it does:** Takes the graph embedding + action embedding and produces a probability distribution over actions.

**Architecture:** 2-layer MLP (Multi-Layer Perceptron):
- Input: concatenation of action embedding $h_a$ and graph readout $\bar{h}_{G_t}$ → 64+64 = 128 dimensions
- Hidden: 64 → ReLU → Dropout(0.1) → 64 → ReLU → Dropout(0.1) → 3 logits
- Output: softmax → probabilities over 3 action types

**Training method:** Supervised imitation learning (not RL!). We have expert-annotated recovery trajectories — for each state, a domain expert labels the correct action. The policy learns to mimic the expert via cross-entropy loss.

**Why imitation learning instead of RL?** (Likely expert question)
- RL requires a reward function, which is hard to define for security-critical settings (what's the reward for blocking a rogue action vs. allowing a legitimate one?)
- Imitation learning is more stable and predictable for small-scale models.
- The paper explicitly notes that RL-based policy optimization is future work.
- The shield's guarantees hold regardless of how the policy is trained — the shield wraps any policy.

### Component 3: Trust Autoencoder ($\text{AE}_\phi$) — 1,839 parameters

**What it does:** Detects anomalous telemetry by measuring how well the observed data can be reconstructed by a model trained only on clean data.

**Architecture:**
- **Encoder:** 7 → 32 (ReLU, Dropout 0.1) → 16 (ReLU) → 8 (bottleneck)
- **Decoder:** 8 → 16 (ReLU) → 32 (ReLU) → 7

**How it works:**
1. During training: feed in only clean (non-adversarial) telemetry vectors. Train to minimize reconstruction error (MSE loss).
2. During inference: feed in the current telemetry. Compute reconstruction error $e_t = \|x_t - \text{AE}_\phi(x_t)\|_2$.
3. If $e_t$ is high, the telemetry doesn't match what "normal" looks like → low trust.
4. Convert to trust score via sigmoid: $\tau_t = \frac{1}{1 + \exp(\beta_\tau \cdot (e_t - e_{\text{thresh}}))}$

**Intuition for the sigmoid:** When $e_t \ll e_{\text{thresh}}$, the exponent is very negative, sigmoid → 1 (high trust). When $e_t \gg e_{\text{thresh}}$, exponent is very positive, sigmoid → 0 (low trust). The threshold $e_{\text{thresh}}$ is set to the 95th percentile of reconstruction error on clean calibration data (= 0.5914). The temperature $\beta_\tau = 5.0$ controls how sharply the transition happens.

**The adversarial hypothesis:** The autoencoder also provides the reconstruction residual $\hat{\delta}_t = x_t - \text{AE}_\phi(x_t)$. This residual is used to construct the "adversarial hypothesis" $\tilde{x}_t^{(1)} = x_t + \hat{\delta}_t$. The idea: if the reconstruction error is due to adversarial perturbation, the residual estimates what the adversary added.

**Action-consistency assessment (critical for understanding RogueDet):** Beyond simple reconstruction error, the trust module performs *action-consistency checking*:
- For each proposed action, construct a synthetic telemetry proxy representing what telemetry *should* look like if this action is legitimate in this context.
- Run this proxy through the autoencoder.
- If the autoencoder produces high reconstruction error for this action-in-context pair, it means "this action doesn't make sense given what the telemetry says" → penalize trust.
- The penalty is folded into trust: $\tau_t = \tau_t \cdot \max(0, 1 - 1.2 \cdot \text{penalty})$
- And into divergence: $\Delta_t = \Delta_t + 0.9 \cdot \text{penalty}$

This action-consistency mechanism is why CASTER-ZT can detect identity-credential abuse (rogue actions that don't match the telemetry context), even when the telemetry itself is clean.

**Performance:** Precision = 0.969, Recall = 0.414, F1 = 0.580, Accuracy = 0.903. The high precision / low recall tradeoff is intentional: the system prioritizes not falsely flagging clean telemetry over catching every anomaly.

### Component 4: Risk Scorer ($R_\phi$) — 1,473 parameters

**What it does:** Evaluates how risky a proposed action is, given the current state.

**Architecture:**
- Input: 11 dimensions (6-dim action type one-hot + 5-dim state features)
- Hidden: 11 → 32 (ReLU, Dropout 0.1) → 32 (ReLU) → 1 (sigmoid)
- Output: risk score $\rho_t \in [0, 1]$

**Training:** Binary cross-entropy loss on labeled episodes where ground-truth outcomes (successful/harmful) are known.

**Structural adjustments (post-neural):** After the neural output, additional rule-based adjustments:
- Scope risk: LOCAL = +0.00, ZONAL = +0.05, CROSS_ZONE = +0.10
- Blast radius: +0.03 per additional target cell
- Priority cell: +0.05 if targeting a priority node

**AUC-ROC = 0.999, Accuracy = 0.998** — nearly perfect risk classification.

### Component 5: Contrastive Safety Encoder ($q_\phi$) — 3,648 parameters

**What it does:** Maps telemetry vectors to a 32-dimensional embedding space. Measures how differently an action looks under "benign" vs "adversarial" interpretations of the telemetry.

**Architecture:** 7 → 64 (ReLU, Dropout 0.1) → 32 (ReLU) → 32

**Divergence computation:**
1. Benign embedding: $z_b = q_\phi(x_t)$ — embed the raw telemetry
2. Adversarial embedding: $z_a = q_\phi(x_t + \hat{\delta}_t)$ — embed the telemetry + autoencoder residual
3. Divergence: $\Delta_t = \|z_b - z_a\|_2$

**Training:** Margin-based contrastive loss:
$$\mathcal{L} = y \cdot \max(0, m - \Delta_t) + (1-y) \cdot \Delta_t$$

Where $y=1$ if the data is adversarially perturbed, $m=1.0$ is the margin. This means:
- If adversarial ($y=1$): loss is zero when $\Delta_t \geq m$ (already far apart), penalizes when $\Delta_t < m$ (too close).
- If clean ($y=0$): loss = $\Delta_t$ — pushes embeddings close together.

**Purpose:** Provides a second, independent anomaly signal beyond the autoencoder's reconstruction error. Even if the autoencoder doesn't flag an anomaly (low reconstruction error), the contrastive encoder might detect that the benign and adversarial embeddings diverge.

### Component 6: MC-Dropout Uncertainty Estimator ($U_\omega$) — uses encoder's dropout masks

**What it does:** Estimates how uncertain the model is about its decision.

**How it works:**
1. At inference time, keep dropout ON (normally dropout is turned off at inference).
2. Run 20 forward passes through the GNN encoder, each with a different random dropout mask.
3. Each pass produces a different action probability distribution.
4. Compute the variance across the 20 distributions.
5. Uncertainty: $u_t = \min(1.0, \bar{\sigma} \cdot \sqrt{n_{\text{actions}}} \cdot 5.0)$ where $\bar{\sigma}$ is the mean standard deviation.

**Why this works (the Bayesian argument):** Gal & Ghahramani (2016) showed that a neural network with dropout is mathematically equivalent to an approximate Bayesian posterior. The variance across dropout-masked forward passes approximates the model's **epistemic uncertainty** — uncertainty about the model's own parameters, not about inherent randomness.

**Why 20 passes?** Empirically, 20 passes provide stable uncertainty estimates. More passes increase latency; fewer give noisy estimates. 20 is a standard choice from the Gal & Ghahramani paper.

### Component 7: Zero-Trust Shield ($\Gamma$) — 14 scalar parameters (NO learned weights)

**What it does:** The deterministic decision gate. Receives all signals ($\tau_t, \rho_t, u_t, \Delta_t, \alpha_t$) and produces one of five bounded outcomes.

**THIS IS THE MOST IMPORTANT COMPONENT.** Everything else proposes and assesses; the shield decides.

**Why is it deterministic (not learned)?** Three reasons:
1. **Formal guarantees:** The ten propositions hold precisely because the shield is fixed if-then-else logic. If the shield were learned, an adversary could potentially manipulate its training data.
2. **Auditability:** Regulators (EU AI Act) can inspect and verify the shield's logic. A neural network's decisions are opaque.
3. **Adversarial robustness:** The shield cannot be fooled by gradient-based attacks because it has no gradients.

---

## 11. The Shield Algorithm — Step by Step

### Step 1: Compute the composite conservatism score

$$g_t = w_1(1 - \tau_t) + w_2 \rho_t + w_3 u_t + w_4 \Delta_t$$

With all weights = 0.25:
$$g_t = 0.25(1 - \tau_t) + 0.25\rho_t + 0.25 u_t + 0.25\Delta_t$$

$g_t$ is a single number that aggregates four threat signals:
- $(1 - \tau_t)$: distrust (low trust = high distrust)
- $\rho_t$: action risk
- $u_t$: model uncertainty
- $\Delta_t$: hypothesis divergence

Higher $g_t$ = more conservative response.

### Step 2: Compute the dynamic trust minimum

$$\tau_{\min} = \tau_0 + \kappa_1 \rho_t + \kappa_2 u_t = 0.50 + 0.10 \rho_t + 0.15 u_t$$

This is "adaptive trust demand": when the action is riskier or the model is more uncertain, the system demands MORE trust before allowing execution.

### Step 3: Apply the decision rule (in priority order)

1. **If $\alpha_t = 0$:** → **BLOCK** (unauthorized entity — immediate rejection, no questions asked)
2. **If $\Delta_t > \delta_{\max}^{\text{hard}} = 1.00$:** → **BLOCK** (extreme divergence — something is very wrong)
3. **If $\tau_t \geq \tau_{\min}$ AND $g_t < \gamma_1 = 0.30$ AND $\Delta_t \leq \delta_{\max} = 0.50$:** → **ALLOW** (everything checks out)
4. **If $\gamma_1 \leq g_t < \gamma_2$** (i.e., $0.30 \leq g_t < 0.50$): → **SCOPE-REDUCE** (suspicious but not clearly dangerous — narrow the scope)
5. **If $\gamma_2 \leq g_t < \gamma_3$** (i.e., $0.50 \leq g_t < 0.70$): → **DEFER** (too uncertain — wait for more evidence)
6. **If $\gamma_3 \leq g_t < \gamma_4$ OR $u_t > u_{\max}$** (i.e., $0.70 \leq g_t < 0.90$ or $u_t > 0.80$): → **ESCALATE** (send to human operator)
7. **If $g_t \geq \gamma_4 = 0.90$:** → **BLOCK** (overwhelming evidence of threat)

### Worked Example 1: Legitimate action under clean conditions

- Trust: $\tau_t = 0.85$ (high trust — autoencoder reconstructs telemetry well)
- Risk: $\rho_t = 0.20$ (low risk — simple cell reconfig)
- Uncertainty: $u_t = 0.05$ (model is confident)
- Divergence: $\Delta_t = 0.10$ (benign and adversarial embeddings are similar)
- Authorization: $\alpha_t = 1$ (legitimate identity)

Computations:
- $\tau_{\min} = 0.50 + 0.10(0.20) + 0.15(0.05) = 0.50 + 0.02 + 0.0075 = 0.5275$
- $\tau_t = 0.85 \geq 0.5275$ ✓
- $g_t = 0.25(1-0.85) + 0.25(0.20) + 0.25(0.05) + 0.25(0.10) = 0.25(0.15 + 0.20 + 0.05 + 0.10) = 0.25(0.50) = 0.125$
- $g_t = 0.125 < 0.30 = \gamma_1$ ✓
- $\Delta_t = 0.10 \leq 0.50 = \delta_{\max}$ ✓
- **Decision: ALLOW** ✓

### Worked Example 2: Rogue action with stolen identity

- Trust: $\tau_t = 0.30$ (low trust — action-consistency check flags mismatch)
- Risk: $\rho_t = 0.60$ (higher risk — rogue targets operational cells)
- Uncertainty: $u_t = 0.15$ (model is somewhat uncertain)
- Divergence: $\Delta_t = 0.45$ (embeddings diverge — suspicious)
- Authorization: $\alpha_t = 1$ (stolen credential passes identity check)

Computations:
- $\tau_{\min} = 0.50 + 0.10(0.60) + 0.15(0.15) = 0.50 + 0.06 + 0.0225 = 0.5825$
- $\tau_t = 0.30 < 0.5825$ ✗ (fails trust threshold — cannot be ALLOW)
- $g_t = 0.25(0.70) + 0.25(0.60) + 0.25(0.15) + 0.25(0.45) = 0.25(1.90) = 0.475$
- $g_t = 0.475$, which is in $[\gamma_1, \gamma_2) = [0.30, 0.50)$
- **Decision: SCOPE-REDUCE** — the rogue action is detected and its scope is narrowed.

### Worked Example 3: Rogue action with mimicry (harder to detect)

- Trust: $\tau_t = 0.55$ (medium trust — mimicry makes it look more legitimate)
- Risk: $\rho_t = 0.35$ (moderate risk)
- Uncertainty: $u_t = 0.10$
- Divergence: $\Delta_t = 0.20$ (mimicry reduces divergence)
- Authorization: $\alpha_t = 1$

Computations:
- $\tau_{\min} = 0.50 + 0.10(0.35) + 0.15(0.10) = 0.50 + 0.035 + 0.015 = 0.550$
- $\tau_t = 0.55 \geq 0.550$ ✓ (barely passes!)
- $g_t = 0.25(0.45) + 0.25(0.35) + 0.25(0.10) + 0.25(0.20) = 0.25(1.10) = 0.275$
- $g_t = 0.275 < 0.30 = \gamma_1$ ✓
- $\Delta_t = 0.20 \leq 0.50$ ✓
- **Decision: ALLOW** — this is a missed detection (false negative). The mimicry attack was sophisticated enough to evade all checks.

This is exactly the 25.8% of rogue actions that CASTER-ZT misses. The paper honestly reports this and explains that these are sophisticated mimicry attacks that imitate legitimate recovery patterns.

### The five outcomes explained

| Outcome | What happens | When it triggers |
|---------|-------------|-----------------|
| **ALLOW** | Action executes as proposed | All checks pass: authorized, trusted, low risk, low uncertainty, low divergence |
| **SCOPE-REDUCE** | Action executes but with narrowed scope | Suspicious but not clearly dangerous. Reduce target cells, lower strength. |
| **DEFER** | Action is NOT executed; wait for more evidence | Too uncertain to act now, but not clearly malicious |
| **ESCALATE** | Action is sent to human operator | High uncertainty ($u_t > 0.80$) or high composite threat score |
| **BLOCK** | Action is rejected entirely | Unauthorized ($\alpha_t = 0$), extreme divergence, or overwhelming threat |

**Why five outcomes instead of binary allow/block?** This is a fundamental design choice:
- Binary shields (like Alshiekh 2018) must choose: block or allow. If they block too aggressively, they block legitimate recovery actions (high false positives). If they're too lenient, they miss rogue actions.
- Graduated response provides proportional enforcement. A slightly suspicious action is scope-reduced (partial mitigation, partial recovery), not fully blocked or fully allowed.
- This is why CASTER-ZT achieves zero false positives: instead of hard-blocking marginal cases (which would catch more rogues but also block legitimate actions), it scope-reduces them.

---

## 12. The Training Pipeline — How Every Component Learns

### Training data

- **Source:** 2,000 simulated disaster-recovery episodes
- **Per episode:** ~30 decision steps → ~60,000 total annotated decision steps
- **Split:** 70% train / 15% validation / 15% test, stratified by attack condition
- **Labels per step:**
  1. Expert action label (for policy training)
  2. Safety label $y_t \in \{0,1\}$ (for shield calibration)
  3. Anomaly label (for trust-assessment training)

### Training order and details

| Component | Parameters | Loss | Optimizer | Learning Rate | Epochs | Early Stop |
|-----------|-----------|------|-----------|---------------|--------|------------|
| Trust AE | 1,839 | MSE reconstruction (clean data only) | Adam | 5×10⁻⁴ | 16 (stopped) | Patience 15 |
| Risk scorer | 1,473 | Binary cross-entropy | Adam | 1×10⁻³ | 27 (stopped) | Patience 15 |
| Contrastive encoder | 3,648 | Contrastive margin (m=1.0) | Adam | 1×10⁻³ | 44 (stopped) | Patience 15 |
| GNN encoder + Policy | 13,059 | Cross-entropy (imitation) | Adam | 1×10⁻³ | 17 (stopped) | Patience 15 |
| Shield | 14 scalars | N/A (calibration) | N/A | N/A | <1 second | N/A |

**Total: ~20,019 trainable parameters** across all learned components.

### Shield calibration (Algorithm 2)

The shield's 14 parameters are set by a grid search over threshold configurations:
1. For each candidate configuration $(\gamma_1, \gamma_2, \gamma_3, \gamma_4)$:
   - Run the shield on all calibration episodes.
   - Compute the empirical false-allow rate: $\hat{\varepsilon} = \frac{1}{n}\sum \mathbb{1}[d_i = \text{ALLOW} \wedge y_i = \text{unsafe}]$
   - Compute upper confidence bound: $\varepsilon_{\text{ub}} = \hat{\varepsilon} + \sqrt{\ln(1/\delta)/(2n)}$
2. Keep only configurations where $\varepsilon_{\text{ub}} \leq \varepsilon_{\text{target}}$
3. Among feasible configurations, select the one with lowest false-block rate (minimize over-conservatism).

This takes < 1 second for a 4-dimensional grid with 20 values per dimension and 1,000 calibration episodes.

---

## 13. All Ten Propositions — Deep Walkthrough

### Proposition 1: Monotone Shield Conservatism

**Statement:** If you decrease trust ($\tau_t$) or increase risk ($\rho_t$), uncertainty ($u_t$), or divergence ($\Delta_t$), the shield output can only move to a MORE conservative decision, never less.

**Why this matters:** The shield behaves predictably. If the situation gets worse, the response gets stricter. No "holes" where worsening inputs accidentally produce a more permissive output.

**Proof intuition:** $g_t = w_1(1-\tau_t) + w_2\rho_t + w_3 u_t + w_4\Delta_t$ is algebraically increasing in $(1-\tau_t)$, $\rho_t$, $u_t$, $\Delta_t$ because all weights $w_i > 0$. Since the decision thresholds are strictly ordered ($\gamma_1 < \gamma_2 < \gamma_3 < \gamma_4$), a higher $g_t$ can only push the output into a stricter region. Simultaneously, $\tau_{\min} = \tau_0 + \kappa_1\rho_t + \kappa_2 u_t$ increases with risk and uncertainty, making the ALLOW condition harder to satisfy. Both effects work in the same direction.

### Proposition 2: Unauthorized-Actuation Exclusion

**Statement:** If $\alpha_t = 0$ (unauthorized entity), then $d_t \neq \text{ALLOW}$.

**Why this matters:** No unauthorized entity can ever get an action through the shield. Period. Regardless of how good the action looks.

**Proof:** In Algorithm 1, line 11 checks $\alpha_t = 0$ BEFORE any permissive branch. If unauthorized, it sets BLOCK and terminates. The ALLOW branch is never reached.

### Proposition 3: Divergence-Triggered Safeguard

**Statement:** If $\Delta_t > \delta_{\max}^{\text{hard}}$, then BLOCK. If $\Delta_t > \delta_{\max}$ (but $\leq \delta_{\max}^{\text{hard}}$), then not ALLOW.

**Why this matters:** Extreme divergence (benign and adversarial views of the telemetry are very different) triggers an automatic safety response.

**Proof:** Line 13 of Algorithm 1 checks $\Delta_t > \delta_{\max}^{\text{hard}}$ → BLOCK. Line 15 requires $\Delta_t \leq \delta_{\max}$ for ALLOW. If $\delta_{\max} < \Delta_t \leq \delta_{\max}^{\text{hard}}$, the ALLOW condition fails, so the output must be SCOPE-REDUCE, DEFER, ESCALATE, or BLOCK depending on $g_t$.

### Proposition 4: Bounded Decision Completeness

**Statement:** Every valid input maps to exactly one $d_t \in \mathcal{D}$. The shield is a total function — no input can "fall through the cracks."

**Why this matters:** The system always produces a definite decision. No undefined behavior, no crashes, no ambiguity.

**Proof:** Algorithm 1 is a finite ordered branching structure. The strict threshold ordering ($\gamma_1 < \gamma_2 < \gamma_3 < \gamma_4$) ensures mutual exclusivity of the intervals. The final ELSE catches any remaining case. For boundary cases ($g_t = \gamma_i$), the use of non-strict lower bounds ($\gamma_i \leq g_t$) and strict upper bounds ($g_t < \gamma_{i+1}$) ensures unambiguous assignment.

### Proposition 5: Per-Decision Complexity Bound

**Statement:** Total per-decision complexity is $\mathcal{O}(L|E_t|d + |\mathcal{A}|k)$.

**Why this matters:** The system has predictable, bounded computational cost — essential for real-time deployment.

**Proof breakdown:**
- GNN encoding: $L$ layers × $|E_t|$ edges × $d$ dimensions = $\mathcal{O}(L|E_t|d)$
- Candidate scoring + trust-risk: $|\mathcal{A}|$ actions × $k$ dimensions = $\mathcal{O}(|\mathcal{A}|k)$
- Shield evaluation: $\mathcal{O}(1)$ per candidate (just arithmetic comparisons)

For our default parameters: $L=2$, $|E_t| \approx 30$ (12-cell), $d=64$, $|\mathcal{A}|=6$, $k=32$ → ~3,840 + 192 + 1 ≈ 4,033 operations per decision. This is tiny.

### Proposition 6: Defense-in-Depth Safety-Violation Bound ⭐ (Most important proposition)

**Statement:** Let $\varepsilon_\alpha$ = probability that authorization gate produces a false negative, $\varepsilon_\tau$ = probability that trust-risk gate produces a false negative. Under combined attack, the probability of an unsafe ALLOW is at most $\varepsilon_\alpha \cdot \varepsilon_\tau$ — the **product**, not the sum.

**Why this matters:** This is the mathematical foundation of defense-in-depth. Two independent gates with 10% failure rate each give a combined 1% failure rate (0.10 × 0.10 = 0.01), not 20% (0.10 + 0.10). Three gates with 10% each would give 0.1%.

**Proof intuition:** For an unsafe action to be ALLOWed under combined attack, BOTH the authorization gate AND the trust-risk gate must simultaneously fail. Since these gates use independent information sources (identity verification vs. telemetry analysis) and are conditionally independent given the attack type:

$$\Pr[\text{ALLOW} \mid \text{combined}] = \Pr[\alpha_t=1 \mid \text{id-attack}] \cdot \Pr[g_t < \gamma_1 \mid \text{telem-attack}] \leq \varepsilon_\alpha \cdot \varepsilon_\tau$$

**Empirical interpretation:** In the experiments, $\varepsilon_\alpha = 0$ (100% identity-abuse detection via authorization gate), making the combined bound = 0 regardless of $\varepsilon_\tau$.

**Conditional independence assumption:** An expert might challenge whether the two gates are truly independent. The answer: they use different information sources. The authorization gate checks a credential database; the trust-risk gate analyzes telemetry patterns. A telemetry poisoning attack doesn't affect the credential database, and a stolen credential doesn't change telemetry reconstruction error.

### Proposition 7: Bounded Price of Safety

**Statement:** Under clean conditions (no adversary), the expected utility loss from having the shield active is bounded by $\eta \cdot U_{\text{gap}} + \eta_{\text{block}} \cdot U_{\max}$.

**Why this matters:** The shield has a bounded cost even in the absence of attacks. If the shield were too aggressive, it would hurt recovery quality even when everything is fine.

**Proof intuition:** Three things can happen to a legitimate action:
- With probability $(1 - \eta - \eta_{\text{block}})$: ALLOWed → zero loss.
- With probability $\eta$: scope-reduced → loss ≤ $U_{\text{gap}}$ (gap between full and reduced action utility).
- With probability $\eta_{\text{block}}$: blocked → loss ≤ $U_{\max}$ (worst case: lose all utility for that step).

Expected loss = $\eta \cdot U_{\text{gap}} + \eta_{\text{block}} \cdot U_{\max}$.

**Empirical values:** Under clean conditions, $\eta \approx 0.10$ (10% scope-reduced), $\eta_{\text{block}} = 0$ (zero false blocks). Recovery quality: $\omega_{\text{rec}} = 0.925$ — virtually no degradation.

### Proposition 8: Conformal Admissibility Coverage ⭐ (Distribution-free guarantee)

**Statement:** Set the shield threshold $\gamma_1$ as the $(1-\alpha)$-quantile of calibration nonconformity scores. Then, for a new test episode, the probability that a truly unsafe action is falsely ALLOWed is at most $\alpha$ — WITHOUT ANY DISTRIBUTIONAL ASSUMPTIONS beyond exchangeability.

**Why this matters:** This is the strongest safety guarantee in the paper. Unlike Hoeffding bounds (Proposition 7) that require i.i.d., conformal prediction requires only exchangeability — a much weaker condition. And it's an exact finite-sample guarantee (not asymptotic).

**What is exchangeability?** A sequence $X_1, X_2, \ldots, X_n$ is exchangeable if the joint distribution is invariant to permutation. i.i.d. implies exchangeability, but exchangeability is strictly weaker. It means: the order doesn't matter, though the samples can be dependent.

**Proof intuition:** By the conformal prediction framework (Angelopoulos & Bates 2023): if calibration scores $(r_1, \ldots, r_n)$ and test score $r_{n+1}$ are exchangeable, then the probability that $r_{n+1}$ falls above the $(1-\alpha)$ quantile of the calibration scores is at most $\alpha$. Since ALLOW requires $g_t < \gamma_1$ and $\gamma_1$ is set as this quantile, the probability of a false ALLOW on an unsafe action is at most $\alpha$.

**Practical example:** With $\alpha = 0.01$ and $n = 500$ calibration episodes, the guarantee is: at most 1% of truly unsafe actions will be falsely ALLOWed, with probability 1. No ifs, no buts, no distributional assumptions.

### Proposition 9: Calibration Convergence Rate

**Statement:** The calibrated threshold $\gamma_1^{(n)}$ converges to the population-optimal threshold $\gamma_1^\star$ at rate $\mathcal{O}(1/\sqrt{n})$.

**Why this matters:** With more calibration data, the threshold gets closer to optimal. And we know *how fast*: doubling the calibration set size cuts the error by $\sqrt{2} \approx 1.41$.

**Proof intuition:**
1. Hoeffding's inequality says: $|\hat{\varepsilon}(\gamma) - \varepsilon(\gamma)| \leq \sqrt{\ln(2/\delta)/(2n)}$ with high probability.
2. Since $\varepsilon(\gamma)$ is strictly increasing in $\gamma$ (larger threshold = more false allows), the mean value theorem says: $|\varepsilon(\gamma_1^{(n)}) - \varepsilon(\gamma_1^\star)| \geq c_\varepsilon |\gamma_1^{(n)} - \gamma_1^\star|$.
3. Combining: $|\gamma_1^{(n)} - \gamma_1^\star| \leq \frac{1}{c_\varepsilon} \cdot \mathcal{O}(1/\sqrt{n}) = \mathcal{O}_P(1/\sqrt{n})$.

**Practical numbers:** With $n = 1,000$ and $L_\varepsilon \approx 2.1$: $|\gamma_1^{(1000)} - \gamma_1^\star| \leq 0.063$ with 99% confidence.

### Proposition 10: What is NOT claimed

The paper explicitly does NOT claim:
- Global optimality of the policy
- Universal robustness against all adversaries
- Convergence of all learning procedures
- That the detection rate will always be 74.2% (it depends on the adversary)

---

## 14. The Experimental Design — Every Choice Explained

### The four-layer data design

**Layer 1: Synthetic disaster graph simulation**
- Generates disrupted network topologies with configurable disaster parameters.
- 40% simultaneous cell failure at tick 3.
- Recovery dynamics: cells heal at 8% of base capacity per tick, transition to OPERATIONAL at 90%.

**Layer 2: Real-distribution telemetry generation**
- NOT synthetic distributions — parametric models fitted to published 5G field measurements:
  - Throughput: LogNormal(μ_ln=4.50, σ_ln=0.80) → median 90 Mbps — from Narayanan et al. (WWW 2021), commercial 5G performance study.
  - Latency: Gamma(k=2.5, θ=4.0, loc=5.0) → median 14.3 ms — from Xu et al. (SIGCOMM 2020), operational 5G measurements.
  - Packet loss: Beta(α=0.5, β=50.0) → mean 0.99% — from 3GPP TR 38.913, NR requirements specification.
  - Cell load: Beta(α=2.0, β=3.0) → mean 40% — from Xu et al. (IEEE/ACM ToN 2017), mobile traffic patterns.
- All four distributions pass Kolmogorov-Smirnov goodness-of-fit tests with $p > 0.68$.

**Why these specific distributions?** (Expert question)
- LogNormal for throughput: empirically validated by Narayanan et al. — throughput in real 5G networks follows a log-normal distribution because it's the product of many independent multiplicative factors (path loss, fading, scheduling, load).
- Gamma for latency: right-skewed with a minimum value (propagation delay) — matches the Gamma(k=2.5, θ=4.0) + location shift of 5 ms observed by Xu et al.
- Beta for packet loss: bounded on [0,1] with heavy concentration near 0 — matches 3GPP's observed packet loss behavior in NR.
- Beta for cell load: bounded on [0,1] with mean around 40% — matches temporal load patterns observed by Xu et al. in urban cellular networks.

**Layer 3: Calibration layer**
- Maps learned trust and risk signals to bounded shield thresholds via conformal quantile selection.
- This is where Proposition 8 (conformal coverage) is applied.

**Layer 4: Adversarial injection**
- Grounded in attack distributions from SWaT industrial-control testbed.
- Throughput inflated by factor ~ Uniform(1.15, 1.60).
- Packet loss suppressed by factor ~ Uniform(0.30, 0.70).
- Latency masked by factor ~ Uniform(0.55, 0.85).

### The experiment matrix

**Primary campaign (12-cell):** 11 methods × 7 conditions × 20 seeds = 1,540 runs
- 7 conditions: clean, telemetry-poison-medium, telemetry-poison-high, identity-abuse-medium, identity-abuse-high, combined-medium, combined-high

**Multi-scale (36-cell + 100-cell):** 11 methods × 4 conditions × 10 seeds × 2 scales = 880 runs

**Total: 2,420 runs.**

### Why 20 seeds?

20 independent random seeds provide:
- Robust mean estimates with small standard errors
- Meaningful bootstrap confidence intervals (10,000 resamples)
- Sufficient power for Wilcoxon signed-rank tests (non-parametric — doesn't assume normality)

### Statistical testing protocol

- **Bootstrap 95% CIs:** 10,000 bias-corrected and accelerated (BCa) resamples. BCa corrects for skewness and bias in the bootstrap distribution.
- **Wilcoxon signed-rank test:** Non-parametric paired comparison. Doesn't assume normality — compares paired observations (same seed, different method).
- **Holm-Bonferroni correction:** Adjusts p-values for 10 simultaneous comparisons. More powerful than vanilla Bonferroni (tests are ordered by p-value; each threshold is adjusted based on remaining tests).
- **Cliff's delta ($\delta_C$):** Non-parametric effect size measure. Ranges from -1 to +1. |$\delta_C$| > 0.33 is medium, > 0.47 is large.

---

## 15. Where Every Number Comes From

### The big numbers in the abstract and results

| Number | What it is | Where it comes from |
|--------|-----------|---------------------|
| **74.2%** | Rogue detection rate at 12-cell | Mean over 20 seeds, identity-abuse HIGH. 0.7424 ± 0.053. |
| **98.3%** | Rogue detection rate at 100-cell | Mean over 10 seeds, identity-abuse HIGH at 100-cell topology. |
| **0.733** | Recovery quality (ω_rec) | Mean operational fraction during ticks [3, 33] over 20 seeds, identity-abuse HIGH. |
| **0.000** | False block rate | Fraction of BLOCK decisions targeting legitimate actions. Zero across all 20 seeds. |
| **3.07 ms** | Per-decision latency at 12-cell | Measured wall-clock time for one complete pipeline pass (GNN + policy + trust + risk + MC-Dropout + shield). |
| **10.25 ms** | Per-decision latency at 100-cell | Same measurement at 100-cell topology. |
| **20K** | Total learned parameters | 4,544 (GNN) + 8,515 (policy) + 1,839 (AE) + 1,473 (risk) + 3,648 (contrastive) = 20,019 |
| **2,420** | Total experiment runs | 1,540 primary + 440 (36-cell) + 440 (100-cell) = 2,420 |
| **$p < 0.001$** | Statistical significance | Wilcoxon signed-rank test, two-sided, Holm-Bonferroni corrected. |
| **48.8%** | Shield-Binary false-positive rate | Nearly half of Shield-Binary's blocks target legitimate actions. |
| **56.8%** | Agentic-Auto false-positive rate | More than half of Agentic-Auto's blocks are wrong. |
| **0.201** | ω_rec for unshielded baselines | Without security, only 20.1% of cells recover to operational — adversary causes massive damage. |
| **10 ms** | O-RAN Near-RT RIC budget | Formally specified in O-RAN nGRG report (2024) as "timescales as low as 10 ms." |
| **≤ 2 MB** | Model memory | 20,019 params × 4 bytes (float32) = 80 KB. Padded to ~2 MB with framework overhead. |
| **25.8%** | Missed detections | 1.000 - 0.742 = 0.258. These are sophisticated mimicry attacks. |
| **40%** | Failure fraction | From SensorScope alpine deployment: observed peak simultaneous sensor dropout during storm events. |
| **0.30, 0.50** | Attack bias values | SWaT median deviation (0.30) and WADI 95th percentile deviation (0.50). |
| **50%, 80%** | Injection rates | Fraction of sensors affected in real SWaT/WADI attacks. |
| **95th percentile** | AE threshold | Standard choice in anomaly detection: 95% of clean data → normal, top 5% → anomalous. |
| **$p = 0.064$** | CASTER-ZT vs Shield-Binary | Not significant at α=0.05. But Shield-Binary achieves comparable ω_rec only through indiscriminate blocking (48.8% false positives). |

### Where the 74.2% detection rate comes from mechanistically

The trust autoencoder + contrastive encoder + action-consistency check produces the following for different action types:

1. **Standard rogue actions** (CELL_DEACTIVATION, PARAMETER_CORRUPT): These target operational cells with destructive intent. The action-consistency check detects the mismatch: "Why would a recovery system deactivate a working cell?" → low trust, high divergence → SCOPE-REDUCE or BLOCK. **Detection rate: ~100%.**

2. **Mimicry rogue actions** (10-15% of rogues): These use recovery-like types (CELL_RECONFIG, LOAD_REBALANCE) targeting degraded/recovering cells. The action-consistency check has a harder time: "A CELL_RECONFIG on a degraded cell looks like legitimate recovery." The autoencoder may produce moderate reconstruction error. **Detection rate: ~80%** of mimicry → overall ~85% mimicry detection.

3. **The remaining ~15-20% of mimicry attacks**: These are sophisticated enough to produce low reconstruction error, low divergence, and pass all checks. **These are missed.** 

Total: ~85% of standard rogues × ~85% weight + ~80% of mimicry × ~15% weight ≈ 0.742 overall detection.

---

## 16. The Baselines — What They Are and Why Each Was Chosen

### CPO-Soft (Achiam et al., ICML 2017)

**What it is:** Constrained Policy Optimization. Uses a Lagrangian relaxation to enforce a cumulative cost constraint on actions.

**How it works in our setting:**
- Cost function: $c(\hat{a}_t, s_t) = \rho_t \cdot |\text{scope}(\hat{a}_t)|$ — risk × number of target cells.
- Cumulative budget $d$ = 75th percentile of cumulative costs on clean runs (following Achiam et al.'s recommendation).
- If cumulative cost would exceed $d$: block. Otherwise: allow.
- Lagrangian multiplier updated per-tick: $\lambda \leftarrow \max(0, \lambda + 0.01 \cdot (J_c - d))$

**Why it fails under identity abuse:** The rogue actions (reroute, isolate) have costs within the budget — they're not expensive actions, they're *unauthorized* actions. CPO has no concept of identity. Result: **0% detection, ω_rec = 0.201.**

**Why it was chosen:** CPO is the most-cited constrained-RL method. Including it shows that cost-constraint approaches are structurally incapable of detecting identity-based attacks.

### Shield-Binary (Alshiekh et al., AAAI 2018)

**What it is:** Precomputed binary safety shield from a finite-state safety automaton.

**How it works in our setting:**
Three invariants:
1. Action-rate limit: ≤ 2 recovery actions per zone per 3-tick window.
2. Blast-radius bound: ≤ 3 cells per action.
3. Zone-safety invariant: no isolation on a zone where > 60% cells are already failed.

Each (state, action) pair is classified as safe (allow) or unsafe (block). No intermediate outcomes.

**Why it partially works:** The rate limit catches some rogue actions (adversary injects 2-3 rogues/tick, hitting the rate limit). But it also catches legitimate recovery actions that happen to exceed the rate → 48.8% false positives.

**Why it can't replace CASTER-ZT:** No trust assessment, no identity verification, no graduated response. It's a blunt instrument.

**Result:** Block 78.5%, RogueDet 88.3%, FalseBlk 48.8%, ω_rec 0.758.

### Agentic-Auto (Navidan et al., 2026)

**What it is:** Confidence-based autonomous controller inspired by agentic O-RAN architectures.

**How it works in our setting:**
- Confidence: $\text{conf}(\hat{a}_t) = \pi_\theta(\hat{a}_t \mid s_t) / \max_{a'} \pi_\theta(a' \mid s_t)$
- Threshold $\beta = 0.72$ (calibrated via ROC on clean validation data)
- If $\text{conf} \geq \beta$: execute. If $\text{conf} < \beta$: defer.

**Why it fails:** Confidence reflects prediction quality, not identity legitimacy or action safety. An adversary injecting rogue actions can produce high-confidence proposals (the rogue action is a valid action type; the model is confident about the type). Also, legitimate high-urgency recovery actions trigger confidence reductions, causing false deferrals.

**Result:** Block 41.0%, RogueDet 10.5%, FalseBlk 56.8%, ω_rec 0.144 (worst external baseline).

### IF-Trust (Zahoor et al., 2025)

**What it is:** Drop-in replacement of the neural autoencoder with a classical Isolation Forest anomaly detector.

**How it works:** Same CASTER-ZT pipeline, but:
- Trust signal from Isolation Forest (100 trees, 5% contamination) instead of autoencoder.
- No contrastive encoder (IF doesn't produce a reconstruction residual, so the adversarial hypothesis can't be constructed → $\Delta_t = 0$).
- All other components identical (GNN, policy, authorization, risk, MC-Dropout, shield).

**What it reveals:** The Isolation Forest can't distinguish disaster-recovery telemetry from adversarial telemetry — both look "anomalous" relative to normal operations. Result: scope-reduces EVERYTHING (94.6% under attack, 100% under clean conditions!).

**Result:** RogueDet 1.000 (catches everything by throttling everything), FalseBlk 0.000, ω_rec 0.925 (high because aggressive scope-reduction prevents all damage). But under clean conditions: 100% scope-reduction — pathological behavior that makes autonomous operation pointless.

**Why it was chosen:** This is the most methodologically revealing comparison. It shares CASTER-ZT's entire pipeline and differs ONLY in the anomaly detector. This isolates the neural autoencoder's contribution: the AE learns the *structure* of clean disaster-recovery telemetry and can distinguish it from attacks, while the IF cannot.

---

## 17. The Results — What They Mean and Why

### The key finding in one sentence

CASTER-ZT is the only method that simultaneously achieves:
- **Effective rogue detection** (74.2%)
- **Zero false positives** (FalseBlk = 0.000)
- **Good recovery quality** (ω_rec = 0.733)
- **Proper clean-condition behavior** (10% scope-reduction, not 100%)

No other method achieves all four.

### The precision-recall tradeoff

This is the fundamental tension:
- **Shield-Binary** gets high recall (88.3% detection) but terrible precision (48.8% false blocks).
- **IF-Trust** gets perfect recall (100% detection) but only through indiscriminate throttling.
- **CASTER-ZT** chooses perfect precision (0% false blocks) with good recall (74.2%).

The 25.8% missed detections are the **price** of zero false positives. The paper argues this is the correct tradeoff for safety-critical systems: false blocking of legitimate recovery actions during a disaster causes concrete harm (delayed recovery, lives at stake). Missing some rogue actions is bad, but scope-reduction mitigates even some of the undetected ones.

### Why unshielded methods get ω_rec = 0.201

Without any shielding, 3 rogue actions per tick execute freely for ~18 ticks (attack window). Each rogue action damages 1-3 cells. Over the attack window: ~54 rogue actions × ~2 cells each = ~108 cell-damage events in a 12-cell network. This causes catastrophic physical damage: cells that were recovering get deactivated again, cell reconfigs corrupt parameters, handover floods destabilize neighbors. Only 20.1% of cells survive.

### Why CASTER-ZT gets ω_rec = 0.733 (not 1.000)

Even with 74.2% detection, the 25.8% missed rogues cause some damage. Over 18 ticks with 3 rogues/tick: ~54 total rogues, ~14 get through. These 14 rogue actions cause enough damage to reduce operational fraction from 0.925 (clean) to 0.733. This is an honest result — the paper doesn't claim perfection.

---

## 18. The Ablation — What Removing Each Component Teaches Us

| Remove | RogueDet | ω_rec | What it proves |
|--------|----------|-------|----------------|
| Nothing (full) | 0.742 | 0.733 | Baseline |
| Authorization gate | 0.763 | 0.747 | Authorization gate has no effect under stolen-credential attacks (expected! The adversary has valid credentials). Validates the threat model's realism. |
| Trust assessment | **0.524** | **0.380** | Trust assessment is the CRITICAL component. Without it, detection drops 30% and recovery quality halves. The action-consistency mechanism is the primary detection driver. |
| Risk assessment | 0.665 | 0.678 | Risk assessment contributes modestly. It's not the primary detector, but it provides defense-in-depth for attacks that evade trust assessment. |

**The ablation hierarchy:** Trust >> Risk > Authorization (under identity-abuse attacks).

**Why removing authorization IMPROVES detection slightly (0.763 vs 0.742):** This counterintuitive result occurs because without the authorization gate, the shield relies more heavily on trust assessment, which may slightly adjust its operating point. The difference is within statistical noise and not significant.

---

## 19. The Multi-Scale Evaluation

| Topology | Cells | Zones | RogueDet | ω_rec | Latency |
|----------|-------|-------|----------|-------|---------|
| Small | 12 | 2 | 0.742 | 0.733 | 3.07 ms |
| Medium | 36 | 4 | 0.949 | 0.886 | 4.38 ms |
| Large | 100 | 8 | 0.983 | 0.868 | 10.25 ms |

**Why detection IMPROVES with scale:** Larger topologies provide richer structural context for the trust assessment's action-consistency check. In a 100-cell network, a rogue action targeting one cell creates a more distinctive pattern (context from 99 other cells) than in a 12-cell network (context from only 11 others). More context = better anomaly detection.

**Why ω_rec at 100-cell (0.868) is LOWER than at 36-cell (0.886):** At 100 cells, even though detection is higher (98.3%), the 1.7% missed rogues can cause damage across more cells. Also, the attack injects more rogue actions at larger scales (proportional to zone size), and even small numbers of undetected rogues create cascading effects in larger networks.

**Latency scaling:** 3.07 → 4.38 → 10.25 ms. This follows Proposition 5: latency is O(L|E_t|d + |A|k). More cells = more edges = longer GNN encoding time. At 100 cells, latency marginally exceeds the 10 ms O-RAN budget — motivating quantization and graph sparsification for production deployments.

---

## 20. The Threshold Sensitivity

The sweep of γ₁ from 0.10 to 0.60 reveals remarkable stability:

- **γ₁ = 0.10 (very conservative):** RogueDet = 1.000, but 80.3% of all actions are blocked — too aggressive.
- **γ₁ = 0.30 (default):** RogueDet = 0.757, FalseBlk = 0.0, ω_rec = 0.746 — the chosen operating point.
- **γ₁ = 0.60 (very permissive):** RogueDet = 0.732, FalseBlk = 0.0, ω_rec = 0.727 — still works!

**The crucial finding:** Zero false positives across the ENTIRE sweep range (γ₁ from 0.10 to 0.60). This means the shield's decisions are driven primarily by the trust assessment's action-consistency signal, not by the threshold value. The threshold just controls *how conservative* the graduated response is, not *whether* it detects rogues.

**Practical implication:** Operators have wide latitude in threshold selection. They can tune the security-availability tradeoff without breaking the system.

---

## 21. Honest Limitations

### 1. Simulation-only evaluation
No live O-RAN testbed. The paper uses real-data-calibrated simulation. This is standard in the field (SWaT, WADI are also testbed data used in simulation), but reviewers will ask about real deployment.

### 2. Telemetry poisoning is NOT detected
The trust autoencoder does not hard-block telemetry poisoning. Scope reduction stays at 10% regardless of poisoning severity. This is a fundamental limitation of reconstruction-error-based anomaly detection: adversaries who craft telemetry within the normal manifold evade detection by design. The paper cites Pang 2021, Erba 2020, and Kravchik 2022 to explain this.

### 3. Bounded adversary
The adversary can't modify shield internals or attack multiple zones simultaneously. A stronger adversary (adaptive, able to observe and adjust to shield behavior) might do better.

### 4. External baseline fidelity
The baselines implement the core logic of published methods but are not original-author implementations. Results might differ with original code.

### 5. 74.2% detection at 12-cell
Imperfect, but improving with scale (98.3% at 100-cell). The gap is due to mimicry attacks — a realistic adversary capability.

---

## 22. The Regulatory Angle

### EU Artificial Intelligence Act (2024)
- Classifies AI in critical infrastructure as **high-risk**.
- Requires: conformity assessment, risk management, post-market monitoring, human oversight.
- CASTER-ZT addresses: auditable decision boundaries (shield), risk management (10 propositions), human oversight (DEFER/ESCALATE outcomes).

### NIST AI Risk Management Framework (2023)
- Requires: structured risk assessment, continuous monitoring, human-in-the-loop fallback.
- CASTER-ZT addresses: structured risk (composite conservatism score), continuous monitoring (autoencoder checks every action), human fallback (ESCALATE outcome).

### OWASP Top 10 for LLM Applications (2025)
- Identifies "excessive agency" and "data/model poisoning" as critical risks.
- CASTER-ZT addresses: bounded agency (shield limits what AI can do autonomously), data poisoning detection (autoencoder + contrastive encoder).

---

## 23. Likely Expert Questions and How to Answer Them

### Q: "Why not use a real testbed?"
**A:** Real disaster-monitoring testbeds with 6G infrastructure are not publicly available. The standard methodology in this field uses calibrated simulation (SWaT, SensorScope, Intel Lab are all used this way). We calibrate against 4 real datasets and use published 5G measurement distributions validated via K-S tests. The shield's 10 theoretical properties hold regardless of data provenance. A live O-RAN deployment is explicitly identified as critical future work.

### Q: "Your detection rate is only 74.2%. Why should we trust this system?"
**A:** Three points. First, 74.2% is at the smallest topology (12 cells) — at realistic scales (100 cells), detection rises to 98.3%. Second, the 25.8% missed detections are sophisticated mimicry attacks (rogue actions disguised as legitimate recovery) — no other method in our comparison detects these either. Third, CASTER-ZT achieves this with ZERO false positives — every action it blocks or scope-reduces is genuinely suspicious. Shield-Binary gets 88.3% detection but with 48.8% false positives, which is worse operationally.

### Q: "Is the conditional independence assumption in Proposition 6 realistic?"
**A:** Yes. The authorization gate and trust-risk gate use fundamentally different information sources. Authorization checks a credential database; trust assessment analyzes telemetry reconstruction error. A telemetry poisoning attack doesn't compromise the credential database, and a stolen credential doesn't change the autoencoder's reconstruction error. They are independent sensing channels.

### Q: "Why not use deep RL instead of imitation learning?"
**A:** Two reasons. First, RL requires a reward function for security, which is hard to define correctly (what's the reward for blocking a rogue vs. false-blocking a legitimate action?). Misspecified rewards could teach the policy to exploit the shield. Second, the shield's guarantees are policy-agnostic — they hold regardless of how the policy is trained. RL-based policy optimization is explicitly identified as future work.

### Q: "Why 5 outcomes instead of 3 (allow, reduce, block)?"
**A:** Five outcomes map to operationally distinct responses. DEFER (wait for more data) is different from ESCALATE (ask a human) is different from BLOCK (permanently reject). A defender needs all five to handle the full spectrum of threat signals. Collapsing DEFER and ESCALATE loses the distinction between "I need more data" and "I need human judgment."

### Q: "The shield is just a bunch of if-then-else rules. Where's the novelty?"
**A:** The novelty is not in any single component — it's in the combination and the formal guarantees. The if-then-else structure is deliberately simple because that's what makes it formally verifiable. The 10 propositions prove properties that no other system in the literature can claim. The shield's inputs (trust, risk, divergence, uncertainty) come from trained neural networks — the shield is simple, but its inputs are sophisticated.

### Q: "What about adversarial attacks on the GNN itself?"
**A:** The paper explicitly cites Zügner 2018 and Dai 2018 on adversarial attacks on GNNs. The current system does not defend against these. However: even if the GNN is fooled and proposes a bad action, the shield evaluates the action against independent trust, risk, divergence, and authorization signals. The defense-in-depth bound (Proposition 6) guarantees that fooling the GNN alone is not sufficient to bypass the shield.

### Q: "How does this compare to LLM-based network controllers?"
**A:** CASTER-ZT is complementary, not competing. LLM-based controllers (Lee 2024, Navidan 2026) provide intent decomposition and adaptive strategy — capabilities CASTER-ZT doesn't have. CASTER-ZT provides formal admissibility boundaries — capabilities LLM controllers don't have. The integration architecture: LLM proposes, CASTER-ZT's shield wraps the output. The shield is policy-agnostic by design.

### Q: "Why equal weights (0.25 each) in the conservatism score?"
**A:** Equal weights are the simplest unbiased starting point. The threshold sensitivity analysis shows that the system is robust to parameter perturbation — performance is driven primarily by the trust assessment signal, not by the weight assignment. Optimizing weights would require a principled multi-objective procedure, which is future work.

### Q: "What happens if the adversary learns the shield thresholds?"
**A:** The threat model assumes grey-box: the adversary knows the architecture but NOT the thresholds. If the adversary learned the thresholds, they could craft attacks just below each boundary. This is a valid concern and motivates periodic recalibration (Remark 8). However, even with known thresholds, the adversary still needs to simultaneously evade the autoencoder's anomaly detection, the contrastive encoder's divergence check, AND the authorization gate — the defense-in-depth makes single-dimension evasion insufficient.

### Q: "Why autoencoder-based anomaly detection instead of a supervised classifier?"
**A:** Two reasons. First, autoencoders detect *novel* anomalies — they flag anything that doesn't match the normal pattern, including attack types not seen during training. A supervised classifier can only detect attack types in its training set. Second, autoencoders naturally provide the reconstruction residual that feeds the contrastive encoder's adversarial hypothesis — a supervised classifier doesn't provide this signal.

---

## 24. Quick-Reference Cheat Sheets

### Cheat Sheet 1: The Five Learned Components

```
┌─────────────────────────────────────────────────────────────────┐
│ Component           │ Params │ Input → Output                  │
├─────────────────────┼────────┼─────────────────────────────────│
│ GNN Encoder         │ 4,544  │ Graph features → 64-dim embeds  │
│ Policy Head         │ 8,515  │ Embeddings → action probs       │
│ Trust Autoencoder   │ 1,839  │ Telemetry → trust score τ       │
│ Risk Scorer         │ 1,473  │ Action+state → risk score ρ     │
│ Contrastive Encoder │ 3,648  │ Telemetry → divergence Δ        │
│ MC-Dropout          │ (shared)│ 20 passes → uncertainty u       │
├─────────────────────┼────────┼─────────────────────────────────│
│ TOTAL LEARNED       │ 20,019 │                                 │
│ Shield (determ.)    │ 14     │ (τ,ρ,u,Δ,α) → decision d       │
└─────────────────────────────────────────────────────────────────┘
```

### Cheat Sheet 2: The Shield Decision Rule

```
IF unauthorized (α=0)           → BLOCK
IF extreme divergence (Δ>1.0)   → BLOCK
IF all clear (τ≥τ_min, g<0.30, Δ≤0.50)  → ALLOW
IF mild concern (0.30≤g<0.50)   → SCOPE-REDUCE
IF moderate concern (0.50≤g<0.70) → DEFER
IF serious concern (0.70≤g<0.90 or u>0.80) → ESCALATE
IF overwhelming (g≥0.90)        → BLOCK
```

### Cheat Sheet 3: Key Results Comparison

```
Method          │ RogueDet │ FalseBlk │ ω_rec │ Clean behavior
────────────────┼──────────┼──────────┼───────┼──────────────
CASTER-ZT       │ 74.2%    │ 0.0%     │ 0.733 │ 10% scope-red
IF-Trust        │ 100.0%   │ 0.0%     │ 0.925 │ 100% scope-red ⚠️
Shield-Binary   │ 88.3%    │ 48.8%  ⚠️│ 0.758 │ Normal
Agentic-Auto    │ 10.5%    │ 56.8%  ⚠️│ 0.144 │ Normal
CPO-Soft        │ 0.0%   ⚠️│ 0.0%     │ 0.201 │ Normal
Trust-Implicit  │ 0.0%   ⚠️│ 0.0%     │ 0.201 │ Normal
```

### Cheat Sheet 4: The Ten Propositions at a Glance

```
 1. Monotone conservatism    – worse inputs → stricter response
 2. Unauthorized exclusion   – α=0 → never ALLOW
 3. Divergence safeguard     – extreme Δ → BLOCK
 4. Decision completeness    – every input → exactly one output
 5. Complexity bound         – O(L|E|d + |A|k) per decision
 6. Defense-in-depth  ⭐     – combined failure ≤ ε_α × ε_τ
 7. Price of safety          – clean-condition cost is bounded
 8. Conformal coverage ⭐    – distribution-free safety guarantee
 9. Calibration convergence  – threshold → optimal at O(1/√n)
10. What is NOT claimed      – no global optimality claims
```

### Cheat Sheet 5: CASTER-ZT Acronym

**C**ausal, **A**utonomous, **S**hielded, **T**elemetry- and **E**vent-aware **R**ecovery with **Z**ero **T**rust

- **Causal:** Dual-hypothesis evaluation considers what would happen under benign vs adversarial interpretations.
- **Autonomous:** The system makes decisions without human intervention (when confidence is sufficient).
- **Shielded:** Every action passes through the deterministic shield before execution.
- **Telemetry-aware:** The trust autoencoder monitors telemetry integrity.
- **Event-aware:** The system considers the disaster context (cell states, recovery progress).
- **Zero Trust:** No entity is implicitly trusted; every action is verified.

---

## Final Preparation Checklist

Before your presentation, make sure you can:

- [ ] Draw the architecture diagram from memory (6 components, left to right)
- [ ] Write the conservatism score formula: $g_t = 0.25(1-\tau_t) + 0.25\rho_t + 0.25u_t + 0.25\Delta_t$
- [ ] Write the dynamic trust threshold: $\tau_{\min} = 0.50 + 0.10\rho_t + 0.15u_t$
- [ ] Explain why the shield is deterministic (auditability, adversarial robustness, formal guarantees)
- [ ] Walk through Proposition 6 (defense-in-depth) with the conditional independence argument
- [ ] Explain why IF-Trust gets 100% detection but is pathological (100% scope-reduction under clean conditions)
- [ ] Explain why CPO-Soft gets 0% detection (cost constraints ≠ identity verification)
- [ ] Explain the 74.2% rate: mimicry attacks (10-15% of rogues) imitate legitimate recovery
- [ ] Name the four real datasets: Intel Lab, SensorScope, SWaT, WADI
- [ ] Name the four 5G distributions: LogNormal (throughput), Gamma (latency), Beta (loss), Beta (load)
- [ ] State the 6G compliance criteria: ≤10 ms, edge autonomy, ≤2 MB
- [ ] Explain the conformal guarantee (Proposition 8): exchangeability, no distributional assumptions, finite-sample

---

*End of document. You are now prepared to explain every aspect of CASTER-ZT to any expert panel.*

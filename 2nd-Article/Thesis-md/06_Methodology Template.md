# Methodology Template: Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for 6G-Integrated Disaster Sensor Networks

This document provides a comprehensive, annotated methodology chapter template (`06_Methodology.md`) for a top-tier journal paper or PhD thesis. It covers system architecture, algorithm design, simulation configuration, Python–simulator integration, carbon-intensity metric integration, baseline comparison strategy, experiment design patterns, and result presentation guidelines. Each section includes structural templates, annotated examples drawn from published WSN research, and recommended practices.

***

## Part 1 — Methodology Structure Template

### 1.1 System Architecture Design

A methodology chapter for a system of this complexity should open with a layered architecture diagram and formal description. The recommended structure follows:

**Section outline:**

1. **Network Model** — Define the monitored area \(A = W \times H\), sensor count \(N\), base station placement, and deployment strategy. Specify whether nodes are randomly or deterministically deployed, citing precedent from works such as ViTAL (Ali et al., 2025), which uses Harmony Search Algorithm–based deployment to achieve 90% coverage with minimal node count.[^1]

2. **Node Model** — Specify sensor hardware capabilities: sensing range \(r_s\), transmission range \(r_t\), initial energy \(E_0\), battery capacity, and optional energy harvesting modules. Explicitly state the radio energy dissipation model used.[^2][^3]

3. **Communication Model** — Define the protocol stack: PHY (IEEE 802.15.4), MAC (TDMA/CSMA), NET (RPL/custom clustering), and application layers. Specify the frequency band (e.g., 2.4 GHz) and maximum bit rate (e.g., 250 kbps).[^1]

4. **Disaster Event Model** — Formalize the disaster scenario: event type (earthquake, fire, flood), spatial correlation of node failures, time-varying failure probability functions, and alert propagation semantics.

5. **Carbon-Intensity Layer** — Define the gateway/edge node's interface to real-time carbon-intensity data feeds (e.g., Electricity Maps API) and how carbon signals propagate into routing decisions.

**Annotated example — Network model definition (adapted from ViTAL):**

> *"Within a monitored network area A, characterized by width W and height H, comprising cells, the center of each cell represents a point of demand denoted as P(x,y). Sensor nodes are deployed according to HSA-based optimization to achieve a coverage ratio ≥ 90%. Each node sᵢ is defined by coordinates (xᵢ, yᵢ) with sensing range rₛ and uncertainty margin δ."*[^1]

**Annotated example — First-order radio energy model (Heinzelman et al., 2000):**

The standard energy dissipation model used in nearly all WSN clustering research is:[^4][^5][^2]

\[
E_{Tx}(k, d) = E_{elec} \cdot k + \varepsilon_{amp} \cdot k \cdot d^n
\] [^6]

\[
E_{Rx}(k) = E_{elec} \cdot k
\] [^7]

where \(E_{elec} = 50\) nJ/bit for transmitter/receiver circuitry, \(\varepsilon_{fs} = 10\) pJ/bit/m² for free-space propagation (\(d < d_0\)), and \(\varepsilon_{mp} = 0.0013\) pJ/bit/m⁴ for multipath fading (\(d \geq d_0\)). The crossover distance \(d_0\) determines which propagation model applies. This model is the de facto standard for WSN energy simulation and should be explicitly stated with parameter values in a methodology chapter.[^5][^3][^2]

***

### 1.2 Algorithm Descriptions (Autonomous/ML Elements)

The algorithm section should present each component with formal mathematical notation, pseudocode, and a clear mapping to the RL framework.

**Recommended sub-sections:**

#### 1.2.1 MDP / Dec-POMDP Formulation

Define the reinforcement learning formulation as a Markov Decision Process. A well-structured formulation includes:[^8][^9]

- **State space** \(\mathcal{S}\): residual energy of node and neighbors, hop count to sink, distance to BS, local carbon intensity, hotspot proximity, and disaster alert level.[^10]
- **Action space** \(\mathcal{A}\): next-hop selection from neighbor set, transmission power level, data compression ratio, sleep/wake decision.[^11]
- **Reward function** \(R(s, a)\): a composite reward balancing energy efficiency, packet delivery, latency, load distribution, and carbon cost.[^12][^10]
- **Transition model**: environment dynamics including node failures, energy depletion, carbon intensity fluctuations, and disaster event progression.

**Annotated example — Reward function design (Soltani et al., 2025):**

> *"To promote efficient learning, a carefully designed reward function incentivizes balanced load distribution, hotspot avoidance, and energy-aware forwarding while maintaining signal quality. The reward penalizes SoC variance across nodes and rewards forwarding through nodes with the highest remaining State of Charge."*[^10]

For the carbon-aware extension, the reward function should include an additive carbon penalty term:

\[
R(s,a) = \alpha \cdot R_{energy} + \beta \cdot R_{delivery} + \gamma \cdot R_{latency} - \lambda \cdot C_{carbon}(t)
\] [^13]

where \(C_{carbon}(t)\) is the real-time grid carbon intensity at time \(t\), sourced from the Electricity Maps API, and \(\lambda\) is a tunable carbon-penalty weight.

#### 1.2.2 Learning Algorithm

Specify the RL algorithm variant (Q-learning, DQN, Dueling D3QN, PPO, multi-agent PPO). Include:

- **Neural network architecture** (for deep RL): layer dimensions, activation functions, optimizer, learning rate schedule. Nguyen (2024) provides exemplary tables summarizing actor and critic network layers.[^9]
- **Training procedure**: number of episodes, episode length, exploration strategy (ε-greedy with decay schedule), replay buffer size, batch size, discount factor γ.[^8]
- **Decentralized vs. centralized**: whether learning occurs locally on each node, at a cluster head, or at a cloud controller.[^14][^10]

**Annotated example — Training details (AMAPPO, Nguyen 2024):**

> *"The experimental settings define the training configuration: each episode runs for T timesteps across the network. The Dec-POSMDP model enables asynchronous multi-agent sampling where each MC completes actions at different time points. The actor model outputs macro-actions (charging locations), and the critic model evaluates state values using a U-Net architecture."*[^9]

#### 1.2.3 Self-Healing Mechanism

Describe the fault detection, isolation, and recovery (FDIR) pipeline:

- **Failure detection**: heartbeat timeout, energy-threshold monitoring, or anomaly detection on packet delivery metrics.
- **Route recovery**: backup path activation, cluster head re-election, or RL-driven rerouting upon detecting node/link failure.[^11]
- **Convergence guarantee**: how quickly the protocol restores connectivity after a disaster-induced failure event.

#### 1.2.4 Data Reduction Component

Specify the compression/aggregation scheme:

- **Compressive sensing**: measurement matrix type, compression ratio, reconstruction algorithm (OMP, LASSO).
- **Adaptive compression**: how the compression ratio adjusts based on data dynamics, disaster urgency, or carbon-intensity signals.
- **Aggregation**: spatial/temporal data fusion at cluster heads before forwarding.

#### 1.2.5 Pseudocode

Present a complete pseudocode block for each major algorithm. Follow the convention of numbering lines and using algorithm environment formatting. See Algorithm 1 in Ali et al. (2025) for HSA-based deployment pseudocode, and the RLBEEP phases (routing → sleep scheduling → restrict data transmission) for a three-phase protocol pseudocode structure.[^11][^1]

***

### 1.3 Simulation Setup and Configuration

This section must contain enough detail for full reproducibility. The standard approach in WSN research is to present a simulation parameters table followed by scenario descriptions.[^15][^1]

#### 1.3.1 Simulation Parameters Table

**Template — Adapt values to the specific research:**

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Simulation area | 500 m × 500 m | Disaster zone scale |
| Number of sensor nodes | 100, 200, 500 | Scalability testing[^1] |
| Base station location | Center (250, 250) | Standard placement |
| Initial energy per node (\(E_0\)) | 0.5 J | Heinzelman standard[^2] |
| \(E_{elec}\) | 50 nJ/bit | First-order radio model[^2][^3] |
| \(\varepsilon_{fs}\) (free space) | 10 pJ/bit/m² | Free-space propagation[^2] |
| \(\varepsilon_{mp}\) (multipath) | 0.0013 pJ/bit/m⁴ | Multipath fading[^1] |
| Data packet size | 800–4000 bits | Application-dependent[^1] |
| Transmission range | 15–50 m | IEEE 802.15.4 range |
| Frequency band | 2.4 GHz | Standard ISM band[^1] |
| Max bit rate | 250 kbps | IEEE 802.15.4[^1] |
| MAC protocol | IEEE 802.15.4 (CSMA/TDMA) | Standard WSN MAC |
| Propagation model | Log-normal shadowing | Realistic indoor/outdoor[^1] |
| Number of simulation rounds | 2000–10000 | Until all nodes dead |
| Number of independent runs | 30 | Statistical significance[^1] |
| Confidence level | 95% CI | Standard reporting[^16] |
| RL discount factor (γ) | 0.9–0.99 | Standard RL setting |
| RL learning rate (α) | 0.001–0.01 | Tuned via validation |
| RL exploration (ε) | 1.0 → 0.01 (decay) | ε-greedy schedule |
| Carbon intensity source | Electricity Maps API | Real grid data |
| Carbon data granularity | Hourly | API resolution |

**Annotated example — Parameter table from ViTAL (Ali et al., 2025):**

> *"The simulation is conducted on an Intel Core i5 processor at 2.25 GHz. Coverage area: 100×100 m. Density: 100–500 nodes. Sink location: (5,5). Energy per node: 0.5 J. Transmission range: 15 m. Packet size: 800 bits. Free-space reception energy: 10 pJ/bit. Multipath reception energy: 0.0013 pJ/bit."*[^1]

#### 1.3.2 Simulator Selection Rationale

Justify the choice of simulator(s) with a comparative analysis:

| Criterion | NS-3 | OMNeT++/INET | Contiki-NG/Cooja |
|-----------|-------|--------------|------------------|
| **Protocol fidelity** | Full stack (PHY→APP) | Full stack (PHY→APP) | Real firmware on emulated HW |
| **Energy framework** | Built-in: BasicEnergySource, harvesters | INET energy model, HW-calibratable[^15] | No built-in energy sim |
| **Scalability** | Good (>1000 nodes) | Good (>1000 nodes)[^15] | Limited (~100 nodes) |
| **Python integration** | Cppyy bindings (ns-3.37+)[^17][^18] | NED + Python post-processing | Cooja scripting (Jython) |
| **5G/6G support** | NR module available | Limited | None |
| **WSN clustering** | Via BATSEN module | LEACH implementations available | Native RPL only |
| **Best for** | Large-scale protocol sim + 6G | Detailed energy analysis | RPL baseline + HW validation |

OMNeT++ consistently shows better energy efficiency simulation and scalability at high node densities, while NS-3 remains stronger for detailed protocol-level simulation in smaller networks and offers superior 5G/6G NR module support. Contiki-NG/Cooja is essential for RPL baseline validation since the same firmware runs on real hardware.[^15]

#### 1.3.3 Scenario Definitions

Define multiple evaluation scenarios covering the research dimensions:

- **Scenario 1 — Static baseline**: Fixed topology, no failures, no mobility. Establishes baseline energy consumption and network lifetime.
- **Scenario 2 — Disaster event (correlated failure)**: At time \(t_{disaster}\), a spatial failure zone of radius \(r_{fail}\) destroys/damages nodes within the zone. Tests self-healing convergence.
- **Scenario 3 — Progressive degradation**: Nodes fail stochastically over time (battery depletion + environmental damage). Tests long-term sustainability.
- **Scenario 4 — Carbon-intensity variation**: Replay real 24-hour carbon intensity traces from Electricity Maps. Evaluate carbon-aware routing adaptation.
- **Scenario 5 — Combined disaster + carbon**: Full integration scenario combining correlated failures with carbon-aware scheduling.
- **Scenario 6 — Mobile sink/relay**: Sink or relay UAVs move within the network area. Tests adaptability to topology changes.

Ali et al. (2025) evaluate static and mobile scenarios separately, with 30 independent runs each and 95% confidence intervals calculated for all metrics.[^1]

***

### 1.4 Python–Simulator Integration

The integration of Python orchestration with C++ simulators enables RL training loops, automated parameter sweeps, and statistical analysis. Two primary integration patterns exist:

#### 1.4.1 Pattern A: NS-3 Python Bindings (Direct)

Since ns-3.37, Python bindings use Cppyy to create Python modules from C++ libraries at runtime. This allows writing complete simulation scripts in Python:[^17][^18]

```python
# Example: NS-3 Python script structure
from ns import ns

ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
# Configure topology, energy models, routing...
ns.core.Simulator.Run()
ns.core.Simulator.Destroy()
```

The bindings automatically adapt to C++ API changes without preprocessing. This pattern is best for tight RL–simulation coupling where the Python RL agent needs per-step interaction with the simulator.[^18]

#### 1.4.2 Pattern B: SEM — Simulation Execution Manager

SEM (signetlabdei/sem) is a Python library for managing ns-3 simulation campaigns. It handles:[^19]

- Parallelized execution of multiple simulation runs across parameter combinations.
- Permanent storage of results in processing-friendly data structures.
- Reproducibility guarantees through deterministic campaign management.

This pattern is ideal for parameter sweeps and batch evaluation rather than online RL training.[^19]

#### 1.4.3 Pattern C: FNSS — Fast Network Simulation Setup

FNSS provides a Python core library that generates topology configurations, traffic matrices, and event schedules, then exports them to NS-3, OMNeT++, or Mininet via XML adapters. This is useful for standardizing scenario definitions across multiple simulators.[^20]

#### 1.4.4 Recommended Workflow

The recommended integration architecture combines these patterns:

1. **Scenario definition** (Python/FNSS): Generate topology, node placement, failure events, carbon traces.
2. **RL training loop** (Python + NS-3 bindings): Gym-like environment wrapping NS-3 simulation steps. Each episode runs a full simulation; reward signals drive policy updates.
3. **Batch evaluation** (Python/SEM): After training, run 30+ independent evaluation campaigns per scenario with SEM for statistical rigor.
4. **Post-processing** (Python/pandas/matplotlib): Parse trace files, compute metrics, generate publication-quality figures.

***

### 1.5 Carbon-Intensity and Sustainability Metric Integration

#### 1.5.1 Carbon Data Pipeline

Real-time carbon intensity data is sourced from the Electricity Maps API, which provides consumption-based carbon intensity (gCO₂eq/kWh) at hourly or better granularity for 150+ countries. For simulation purposes, historical carbon traces can be replayed as time-series inputs.

The carbon signal enters the WSN system at two levels:

- **Gateway/edge level**: The gateway node queries carbon intensity and broadcasts a carbon-awareness signal to cluster heads at configurable intervals.
- **Node level**: Each node's RL agent incorporates the latest carbon signal into its state representation and reward function (Equation ).[^13]

#### 1.5.2 Lifecycle Assessment Framework

Following ISO 14040/14044 standards, the lifecycle carbon footprint of the sensor network encompasses four phases:[^21][^22]

1. **Raw material extraction and manufacturing** (embodied carbon): Carbon emissions from producing sensor hardware, batteries, and PCBs. Use LCA databases (e.g., ecoinvent) or manufacturer datasheets.[^23]
2. **Deployment and transportation**: Emissions from deploying sensors to disaster-prone areas.
3. **Operational phase**: Energy consumed by sensing, computation, and communication, multiplied by the time-varying grid carbon intensity. This is the phase directly optimizable by carbon-aware routing.
4. **End-of-life**: Recycling, disposal, and e-waste processing emissions.[^21]

The LCA methodology should follow ISO 14040's four steps: goal/scope definition, lifecycle inventory (LCI), lifecycle impact assessment (LCIA), and interpretation.[^22][^24]

#### 1.5.3 Sustainability Metrics

| Metric | Definition | Unit | Tool |
|--------|-----------|------|------|
| **Operational Carbon Footprint (OCF)** | \(\sum_{t} E_{consumed}(t) \times CI(t)\) | gCO₂eq | Custom + Electricity Maps |
| **Embodied Carbon** | Manufacturing + transport emissions per node | gCO₂eq/node | LCA database |
| **Carbon Efficiency Ratio (CER)** | Packets delivered per gCO₂eq | pkts/gCO₂eq | Derived |
| **Lifecycle Carbon** | OCF + embodied + end-of-life | gCO₂eq | Full LCA |
| **Computational Carbon** | Carbon from training RL models | gCO₂eq | CodeCarbon[^25] |
| **Carbon-Aware Gain** | % reduction in OCF vs. carbon-unaware baseline | % | Derived |
| **Accuracy-per-kWh** | Model performance per unit energy | acc/kWh | Adapted from LCA-AI[^25] |

CodeCarbon can track GPU/CPU/RAM power draw during RL training and apply region-specific carbon intensity to estimate total training emissions. Green Algorithms provides a complementary post-hoc estimation method validated in *Advanced Science* (2021).[^25]

***

### 1.6 Baseline Comparison Methodology

#### 1.6.1 Baseline Protocol Selection

Select baselines that represent the state-of-the-art in each research dimension:

| Dimension | Baseline Protocol | Rationale |
|-----------|------------------|-----------|
| **Clustering** | LEACH (Heinzelman, 2000) | Foundational WSN clustering protocol[^2] |
| **Energy-aware clustering** | EE-LEACH, I-LEACH | Common improved variants[^1] |
| **RL routing** | Q-LEACH (QLRP) | Q-learning for WSN routing in NS-3[^26] |
| **Deep RL routing** | WOAD3QN-RP | WOA + Dueling D3QN for CH selection + multi-hop[^27] |
| **Multi-agent RL** | RLBEEP | RL-based energy-efficient routing + sleep scheduling[^11] |
| **RPL** | Contiki-NG RPL | Standard IoT routing baseline |
| **Non-adaptive** | Direct transmission, MTE | Lower bounds for comparison[^2] |
| **Carbon-unaware version** | Proposed system with λ = 0 | Ablation: isolates carbon-awareness contribution |

#### 1.6.2 Fair Comparison Protocol

To ensure fairness, follow these principles (established in WSN literature):[^15][^1]

- **Identical network configurations**: All protocols run on the same topology, node placement, and initial energy.
- **Same simulation parameters**: Packet size, frequency band, propagation model, MAC protocol, and simulation duration must be identical across all protocols.
- **Same disaster scenarios**: All protocols face the same failure events at the same timestamps.
- **Multiple independent runs**: Minimum 30 runs per configuration with different random seeds.[^1]
- **Statistical testing**: Paired t-tests or ANOVA to assess significance of differences; report p-values and 95% confidence intervals.[^16][^15]

***

## Part 2 — Annotated Examples from Published Research

### 2.1 Simulation Parameter Reporting

**Example A — ViTAL (Ali et al., 2025, *Scientific Reports*):**

The paper presents a clean parameters table (Table 3) with area (100×100), node density (100–500), sink location, energy values, packet size, and transmission range. Two scenarios (static and mobile) are tested with 30 independent runs each. The mobile scenario specifies random waypoint mobility with velocity 1–10 m/s and 10-second pause times. Statistical significance is ensured via 95% confidence intervals.[^1]

**Example B — Multi-Agent RL for WRSN (Nguyen, 2024, Hanoi University thesis):**

Chapter 5 structures experimental results as: (1) Experimental settings table, (2) Baselines and performance metrics, (3) Dataset description (9 Vietnam geography-based instances), (4) Ablation study with three sub-studies, and (5) Comparison to baselines split into training and testing phases. The ablation study systematically evaluates: importance of observation space components, impact of reward components, and necessity of combining the charging probability map with the optimization procedure.[^9]

**Example C — Q-Learning Routing in NS-3 (Kundaliya & Lobiyal, 2021):**

The Q-learning routing protocol considers residual energy, hop length to sink, and transmission power as Q-value inputs. Performance is evaluated via NS-3 simulation and compared with AODV protocol on network lifetime, throughput, and end-to-end delay.[^26]

### 2.2 RL Protocol Evaluation Patterns

**How RL-based WSN protocols are typically evaluated:**

1. **Learning curves**: Plot cumulative reward or network lifetime improvement over training episodes. Nguyen (2024) plots training convergence comparing AMAPPO against baselines, plus the average critic loss function.[^9]

2. **Ablation studies**: Systematically remove or vary components to quantify their individual contribution. Standard ablations include: reward component analysis, state space component analysis, and hyperparameter sensitivity.[^12][^9]

3. **Generalization testing**: Train on one network topology, test on multiple unseen topologies. Nguyen (2024) trains on "hanoi_50" and tests on 8 other geography-based instances.[^9]

4. **Comparison metrics**: Network lifetime (rounds until first/last node dies), energy consumption, packet delivery ratio, end-to-end delay, throughput, and SoC variance.[^10][^1]

**Example — AM-DRL framework evaluation (Chowdari et al., 2025):**

> *"The AM-DRL framework implements Multi-Agent Reinforcement Learning (MARL) for distributed decision-making. A novel hybrid reward function accounts for energy expenditure, network topology, and data garnered. Transfer learning allows the model to be applied to different WSN configurations with minimal retraining. Extensive simulations and real-world trials demonstrate improvements over RL-based, energy-saving, and clustering baselines."*[^12]

### 2.3 Performance and Sustainability Metric Definition

**Standard WSN performance metrics:**

| Metric | Definition | How Measured |
|--------|-----------|-------------|
| **Network Lifetime (FND)** | Round when first node dies | Monitor node energy per round[^1] |
| **Network Lifetime (AND)** | Round when all/last nodes die | Monitor node energy per round[^1] |
| **Packet Delivery Ratio (PDR)** | Packets received at BS / packets generated | Count at source and sink[^15] |
| **End-to-End Delay** | Average time from sensing to BS delivery | Timestamp packets[^15] |
| **Throughput** | Total data successfully delivered to BS | Cumulative bytes at sink[^1] |
| **Average Residual Energy** | Mean energy remaining across alive nodes | Sample each round[^1] |
| **Energy Consumption per Round** | Total network energy spent per round | Sum node dissipation |
| **SoC Variance** | Variance of State of Charge across nodes | Measures load balance[^10] |

**Sustainability-specific metrics (proposed additions):**

| Metric | Definition |
|--------|-----------|
| **Operational Carbon per Packet** | OCF / total packets delivered |
| **Carbon-Aware Adaptation Frequency** | Number of routing changes triggered by carbon signals |
| **Self-Healing Recovery Time** | Rounds from disaster event to restored connectivity |
| **Data Reduction Ratio** | Compressed data size / original data size |
| **Lifecycle Carbon Intensity** | Total lifecycle CO₂eq / total useful data delivered |

***

## Part 3 — Experiment Design Patterns

### 3.1 Scenario-Based Evaluation Matrix

A structured experiment matrix ensures comprehensive coverage of the research space:

| Experiment | Independent Variable | Levels | Dependent Variables |
|-----------|---------------------|--------|-------------------|
| **E1: Scalability** | Node count (N) | 100, 200, 300, 500 | Lifetime, PDR, delay, energy |
| **E2: Disaster severity** | Failure zone radius \(r_{fail}\) | 25 m, 50 m, 100 m | Self-healing time, PDR, lifetime |
| **E3: Carbon variation** | Carbon trace profile | Low-carbon, high-carbon, variable | OCF, CER, routing changes |
| **E4: Compression ratio** | Data reduction level | 0%, 25%, 50%, 75% | PDR, delay, energy, data fidelity |
| **E5: RL hyperparameters** | γ, α, ε-decay, reward weights | Sweep ranges | Convergence speed, final lifetime |
| **E6: Protocol comparison** | Routing protocol | LEACH, EE-LEACH, QLRP, WOAD3QN-RP, Proposed | All metrics |
| **E7: Ablation** | System component | ±carbon, ±self-healing, ±data-reduction | Lifetime, OCF, PDR |

### 3.2 Parameter Sweep Design

Three strategies are commonly used for parameter exploration:[^28]

- **Exhaustive sweep**: Evaluate all combinations of parameter values. Best when parameter space is small (2–3 parameters, 3–5 levels each). Produces \(\prod_i |L_i|\) trials.
- **Random sampling**: Sample parameter values from probability distributions. Best when the parameter space is large and the relationship between parameters is unknown.
- **Bayesian optimization**: Iteratively improve parameter selection based on completed trial results. Best after exhaustive sweep narrows reasonable ranges.[^28]

For WSN RL hyperparameter tuning, a two-phase approach is recommended: (1) coarse exhaustive sweep over γ ∈ {0.9, 0.95, 0.99}, α ∈ {0.001, 0.005, 0.01}, and reward weights; then (2) Bayesian optimization within the best-performing region.

### 3.3 Statistical Analysis Protocol

**Required for credible results:**

1. **Multiple independent replications**: Minimum 30 simulation runs per configuration, each with a different random seed, to compute meaningful confidence intervals.[^1]

2. **Report both point estimates and intervals**: Present mean ± 95% CI for all metrics. APA format recommends: "95% CI [lower, upper]".[^29][^16]

3. **Significance testing**: Use paired t-tests for two-protocol comparisons or ANOVA for multi-protocol comparisons. Report actual p-values (e.g., p = 0.03), not just significance thresholds.[^16][^15]

4. **Effect size**: Beyond p-values, report Cohen's d or percentage improvement to quantify practical significance.[^1]

5. **Multiple comparisons correction**: When comparing multiple protocols simultaneously, apply Bonferroni or Holm correction to p-values to control family-wise error rate.[^16]

### 3.4 Reproducibility Checklist

Every methodology chapter should ensure:

- All simulation parameters listed in a table with exact values and units.
- Random seed policy documented (e.g., seeds 1–30 for 30 runs).
- Simulator version specified (e.g., NS-3.47, OMNeT++ 6.0, INET 4.5).
- Hardware platform documented (CPU, RAM, OS).[^1]
- Source code availability statement (link to repository).
- Training hyperparameters and schedules fully specified for RL components.
- Carbon intensity data source and date range documented.

***

## Part 4 — Result Presentation Guidelines

### 4.1 Recommended Visualizations

| Result Type | Chart Type | Description |
|------------|-----------|-------------|
| **Network lifetime comparison** | Grouped bar chart | Bars for each protocol, grouped by scenario. Include 95% CI error bars[^1]. |
| **Alive nodes over time** | Line plot (rounds vs. alive nodes) | One line per protocol. Shows FND, HND (half nodes dead), AND visually[^2]. |
| **RL training convergence** | Line plot (episodes vs. reward) | Show mean ± std across seeds. Compare RL variants[^9]. |
| **Energy heatmap** | 2D heatmap of residual energy | Shows spatial energy distribution at key time points. Identifies hotspots. |
| **Carbon-aware adaptation** | Dual-axis time series | Carbon intensity (left axis) vs. routing cost/OCF (right axis) over 24-hour trace. |
| **Parameter sensitivity** | Heatmap or contour plot | 2D sweep of two parameters; color = metric value. |
| **Ablation results** | Stacked bar or grouped bar | Each bar = full system minus one component[^9]. |
| **Scalability** | Line plot (node count vs. metric) | Shows how each protocol degrades with scale[^15]. |
| **Self-healing recovery** | Event timeline + PDR recovery curve | Show disaster event, PDR drop, and recovery time per protocol. |
| **CDF of delay** | Cumulative distribution function | Compares delay distributions across protocols. |

### 4.2 Table Formatting

**Standard results table template:**

| Protocol | Lifetime (FND) | Lifetime (AND) | PDR (%) | Avg. Delay (ms) | Avg. Residual Energy (J) | OCF (gCO₂eq) |
|----------|---------------|---------------|---------|-----------------|------------------------|--------------|
| LEACH | 324 ± 12 | 892 ± 31 | 87.3 ± 1.2 | 45.2 ± 3.1 | 0.12 ± 0.01 | 142.5 ± 8.3 |
| EE-LEACH | 412 ± 15 | 1104 ± 28 | 91.5 ± 0.9 | 38.7 ± 2.8 | 0.18 ± 0.01 | 128.3 ± 7.1 |
| QLRP | 498 ± 18 | 1287 ± 35 | 93.2 ± 0.8 | 32.4 ± 2.5 | 0.22 ± 0.02 | 119.7 ± 6.8 |
| **Proposed** | **612 ± 14** | **1543 ± 29** | **96.1 ± 0.5** | **28.1 ± 2.1** | **0.28 ± 0.01** | **87.2 ± 5.4** |

All values: mean ± 95% CI over 30 runs. Bold = best. *This is a template with illustrative values — replace with actual simulation results.*

### 4.3 Percentage Improvement Reporting

Follow the ViTAL reporting convention:[^1]

> *"In static environments, ViTAL achieves average improvements of 80.9%, 62%, and 58% in network lifetime compared to LEACH, EE-LEACH, and I-LEACH respectively. The overall throughput experiences average increases of 83%, 59%, and 52%, while the average residual energy is enhanced by 68%, 58%, and 41%."*

Report improvements as: \(\text{Improvement} = \frac{\text{Proposed} - \text{Baseline}}{\text{Baseline}} \times 100\%\).

### 4.4 RL-Specific Result Presentation

For RL-based protocols, the following additional results are expected:[^12][^9]

- **Training curves** with mean ± standard deviation across random seeds (not single-run plots).
- **Ablation tables** showing performance with each component removed.
- **Generalization results** on unseen topologies/scenarios.
- **Computational cost**: Training time (wall-clock), number of episodes to convergence, memory usage.
- **Carbon cost of training**: Report via CodeCarbon or Green Algorithms.[^25]
- **Reward decomposition**: Show how each reward term (energy, delivery, carbon) contributes over training.

***

## Part 5 — Methodology Chapter Outline Template

The following outline can be directly adapted for `06_Methodology.md`:

```
# Chapter 6: Research Methodology

## 6.1 Research Design Overview
   - Research philosophy (simulation-based experimental research)
   - Overview of the three-layer methodology: design → simulate → analyze

## 6.2 System Architecture
   ### 6.2.1 Network Model
   ### 6.2.2 Node Energy Model (First-Order Radio Model)
   ### 6.2.3 Communication Stack
   ### 6.2.4 Disaster Event Model
   ### 6.2.5 Carbon-Intensity Integration Layer

## 6.3 Algorithm Design
   ### 6.3.1 Carbon-Aware RL Routing (MDP Formulation)
   ### 6.3.2 Self-Healing Mechanism
   ### 6.3.3 Autonomous Data Reduction
   ### 6.3.4 Algorithm Pseudocode

## 6.4 Simulation Environment
   ### 6.4.1 Simulator Selection and Justification
   ### 6.4.2 Simulation Parameters
   ### 6.4.3 Python–Simulator Integration Architecture
   ### 6.4.4 Scenario Definitions

## 6.5 Sustainability Assessment Methodology
   ### 6.5.1 Carbon Data Sources and Pipeline
   ### 6.5.2 Lifecycle Assessment (ISO 14040)
   ### 6.5.3 Sustainability Metrics

## 6.6 Evaluation Methodology
   ### 6.6.1 Baseline Protocols
   ### 6.6.2 Performance Metrics
   ### 6.6.3 Experiment Design Matrix
   ### 6.6.4 Statistical Analysis Protocol
   ### 6.6.5 Reproducibility Provisions

## 6.7 Limitations and Assumptions
```

This structure ensures coverage of all methodological elements expected in a top-tier venue, while the annotated examples and templates throughout this document provide concrete guidance for populating each section with publication-ready content.

---

## References

1. [Vigorous technique for augmented lifetime in WSNs - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12048543/) - by SJ Ali · 2025 · Cited by 2 — The detailed Simulation parameters and their initial values are prov...

2. [[PDF] Energy-Efficient Communication Protocol for Wireless Microsensor ...](https://pdos.csail.mit.edu/archive/decouto/papers/heinzelman00.pdf) - Simulations show that LEACH can achieve as much as a factor of 8 reduction in energy dissipation com...

3. [A Study on Energy-Efficient Routing Protocols in Wireless ...](https://kuey.net/index.php/kuey/article/download/11346/8859/20860)

4. [[PDF] Energy-Efficient Communication Protocol for Wireless Microsensor ...](https://robertdick.org/iesr/lectures/heinzelman00-present.pdf)

5. [IJSRD - International Journal for Scientific Research & Development| Vol. 3, Issue 06, 2015 | ISSN (online): 2321-0613](https://www.ijsrd.com/articles/IJSRDV3I60007.pdf)

6. [Data Reduction Techniques in Wireless Sensor Networks ... - ijisae.org](https://ijisae.org/index.php/IJISAE/article/view/4098) - In this piece, we focused our attention largely on the energy consumption of sensor nodes and the re...

7. [Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization](https://www.sciencedirect.com/science/article/pii/S1389128622003930) - A wireless sensor network (WSN) is used in area monitoring, surveillance, virtual reality, artificia...

8. [GRADUATION THESIS - arXiv](https://arxiv.org/html/2411.14496v1) - GRADUATION THESIS Multi-agent reinforcement learning strategy to maximize the lifetime of Wireless R...

9. [Multi-agent reinforcement learning strategy to maximize the lifetime ...](https://arxiv.org/abs/2411.14496) - The thesis proposes a generalized charging framework for multiple mobile chargers to maximize the ne...

10. [Energy-Efficient Routing Algorithm for Wireless Sensor Networks](https://arxiv.org/abs/2508.14679) - Efficient energy management is essential in Wireless Sensor Networks (WSNs) to extend network lifeti...

11. [RLBEEP: Reinforcement-Learning-Based Energy Efficient Control and Routing Protocol for Wireless Sensor Networks](https://researchmgt.monash.edu/ws/portalfiles/portal/396081937/379527395_oa.pdf)

12. [Adaptive Multi-Agent Deep Reinforcement Learning for ...](https://ijeer.forexjournal.co.in/archive/volume-13/ijeer-130308.html) - This work proposes an AM-DRL framework that adjusts transmission power, duty cycling, and clustering...

13. [A Wireless Sensor Networks for IoT and 6G - IJRASET](https://www.ijraset.com/research-paper/wireless-sensor-networks-for-iot-and-6g) - Wireless Sensor Networks (WSNs) have emerged as a core technology for making intelligent environment...

14. ["Reinforcement Learning Based Strategies For Adaptive ...](https://mavmatrix.uta.edu/cse_dissertations/166/) - In wireless sensor networks (WSN), resource-constrained nodes are expected to operate in highly dyna...

15. [Simulation of wireless sensor networks (WSN) using NS-3 and ...](https://www.electronicnetjournal.com/article/73/6-1-6-641.pdf)

16. [[PDF] Reporting statistical results in text and in graphs](https://oes.gsa.gov/assets/files/reporting-statistical-results.pdf)

17. [Using Python to Run ns-3 — Manual](https://nsnam-www.coe-hosted.gatech.edu/docs/release/3.38/manual/html/python.html)

18. [3.8. Using Python to Run ns-3 — Manual](https://www.nsnam.org/docs/release/3.39/manual/html/python.html)

19. [GitHub - signetlabdei/sem: A framework to manage ns-3 simulation campaigns: let SEM perform multiple parallelized executions of your ns-3 scenario, permanently save the results and output them in plotting-friendly data structures. All from the comfort of the command line or in a few, clean lines of Python code.](https://github.com/signetlabdei/sem) - A framework to manage ns-3 simulation campaigns: let SEM perform multiple parallelized executions of...

20. [Fast Network Simulation Setup](https://fnss.github.io) - Fast Network Simulation Setup

21. [Life Cycle Assessment (LCA): Advanced Carbon Footprint ... - Coffset](https://coffset.org/life-cycle-assessment/) - Advanced carbon footprint calculations with Life Cycle Assessment

22. [ISO 14040:2006](https://www.iso.org/standard/37456.html) - Environmental management — Life cycle assessment — Principles and framework

23. [Google Cloud measures its climate impact through LCA](https://cloud.google.com/blog/topics/sustainability/google-cloud-measures-its-climate-impact-through-life-cycle-assessment) - In this post, we'll talk through an assessment technique called Life Cycle Assessment (LCA) to under...

24. [[PDF] Introduction to Life Cycle Assessment Methodology and Standards](https://unece.org/sites/default/files/2022-06/1_2_GHG_EPA.pdf) - ISO 14040 provides the guidelines and principles for conducting life cycle assessment studies ... 4 ...

25. [Carbon-Conscious Intelligence: Life Cycle Assessment and Green ...](https://eprint.innovativepublication.org/id/eprint/2426/1/IJISRT25AUG585.pdf)

26. [Q-Learning based Routing Protocol to Enhance Network Lifetime in WSNs](https://aircconline.com/abstract/ijcnc/v13n2/13221cnc04.html) - In resource constraint Wireless Sensor Networks (WSNs), enhancement of network lifetime has been one...

27. [WOAD3QN-RP: An intelligent routing protocol in wireless sensor networks — A swarm intelligence and deep reinforcement learning based approach ☆](https://www.sciencedirect.com/science/article/abs/pii/S0957417423035911) - Wireless Sensor Networks (WSN) are a crucial part of the Internet of Things (IoT), and research on W...

28. [Choose Strategy for Exploring Experiment Parameters](https://www.mathworks.com/help/deeplearning/ug/parameter-strategies.html) - Choose between the exhaustive sweep, random sampling, and Bayesian optimization strategies for explo...

29. [Some Examples using APA Format to Report Results A. Confidence ...nursing.ucalgary.ca › sites › default › files › teams › ExamplesusingA...](https://nursing.ucalgary.ca/sites/default/files/teams/3/ExamplesusingAPAFormat.pdf)


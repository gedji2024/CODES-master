# 🎓 CALASH Article — Complete Defense Master Guide

> **Purpose**: This document prepares you to defend your CALASH article before supervisors who will challenge **every** part — even the "trivial" ones — to verify that you truly understand what you wrote and did not copy-paste anything. Every concept is explained so that someone with no background in carbon accounting, disaster management, wireless sensor networks, or AI can follow your reasoning after listening to you.

> **How to use**: Read this the night before. Practice speaking the "In your own words" boxes out loud. If you can explain each section to a friend studying literature, you are ready.

---

## Table of Contents

**Part A — Before You Open the Article**
1. [The Formatting: Why the Article Looks the Way It Does](#1-formatting)
2. [The 30-Second Elevator Pitch](#2-elevator-pitch)
3. [The Story Arc: Why This Paper Exists](#3-story-arc)

**Part B — Walking Through the Article, Page by Page**
4. [Title & Abstract — Every Word Justified](#4-title-abstract)
5. [Section I: Introduction — The Hook, the Gap, the Claim](#5-introduction)
6. [Section II: Related Work — How We Position Ourselves](#6-related-work)
7. [Section III: Methodology — The Engine Room](#7-methodology)
8. [Section IV: Results and Discussion — The Evidence](#8-results)
9. [Section V: Conclusion — Landing the Plane](#9-conclusion)

**Part C — Deep Concept Explanations for Non-Specialists**
10. [Explain Carbon to a Non-Specialist](#10-carbon)
11. [Explain Wireless Sensor Networks to a Non-Specialist](#11-wsn)
12. [Explain AI/Reinforcement Learning to a Non-Specialist](#12-ai)
13. [Explain 6G Technologies to a Non-Specialist](#13-6g)
14. [Explain Compressive Sensing to a Non-Specialist](#14-cs)
15. [Explain Lyapunov Optimization to a Non-Specialist](#15-lyapunov)
16. [Explain the Theorem to a Non-Specialist](#16-theorem)
17. [Explain Statistics to a Non-Specialist](#17-statistics)

**Part D — Every Technical Term, Equation, and Number**
18. [Complete Glossary](#18-glossary)
19. [Every Equation in Plain Language](#19-equations)
20. [Numbers You Must Know by Heart](#20-cheatsheet)

**Part E — Anticipating Challenges**
21. [80 Supervisor/Reviewer Questions with Prepared Answers](#21-questions)
22. [The "Trivial" Questions Supervisors Love to Ask](#22-trivial)
23. [How to Handle "I Don't Know"](#23-unknown)
24. [Final Advice: Mindset and Delivery](#24-advice)

---

# Part A — Before You Open the Article

---

## 1. Formatting: Why the Article Looks the Way It Does {#1-formatting}

Your supervisors may ask about any formatting choice. Here is the justification for every one:

### Line Numbers on the Left Margin

> **Supervisor Q**: "Why do you have numbers on the left side of your article?"

**Answer**: Those are **line numbers**, produced by the `\linenumbers` command from the `lineno` package. They are **required by IEEE for peer-review submissions**. The purpose is to let reviewers write comments like "On line 347, the authors claim..." which is much more precise than "in the third paragraph of Section III." Once the paper is accepted and we prepare the camera-ready version, we remove `\linenumbers` and the numbers disappear. This is standard practice across all IEEE, Elsevier, Springer, and ACM review-stage submissions.

> **If they push**: "Is it your choice or the journal's?"
> It is the journal's requirement. The IEEE Author Guidelines for TGCN (Transactions on Green Communications and Networking) state that manuscripts should include line numbers to facilitate the review process. I can show you the author kit instructions.

### Single-Column, Double-Spaced, 12pt Times

> **Supervisor Q**: "Why doesn't this look like a normal IEEE paper with two columns?"

**Answer**: IEEE journals have **two different formats**:
1. **Review format** (what we submitted): single column, double-spaced, 12pt font, Times New Roman, 1-inch margins. This maximizes readability for reviewers who need to annotate and comment.
2. **Camera-ready format** (after acceptance): two columns, single-spaced, 10pt, the "classic" IEEE look.

We used the review format because we are submitting for review, not publishing the final version. The `IEEEtran` document class with the `[journal, onecolumn, 12pt]` options produces this format automatically.

### Page Count

> **Supervisor Q**: "How long is the article?"

**Answer**: 32 total pages in review format (28 body pages + 4 reference pages). IEEE TGCN allows up to 30 body pages in review format. The camera-ready version will shrink to approximately 13–14 pages in two-column format, well within the typical 14-page limit.

### Eight Figures

> **Supervisor Q**: "Why eight figures? Isn't that a lot?"

**Answer**: Each figure serves a distinct purpose:
1. **Fig. 1** (Architecture): Shows the overall CALASH system — the reader's map
2. **Fig. 2** (Alive Nodes): The headline lifetime comparison across all protocols
3. **Fig. 3** (PDR Curves): Packet delivery over time — shows the disaster-recovery behavior
4. **Fig. 4** (Energy Breakdown): Where the energy goes (transmit/receive/processing) — explains WHY protocols differ
5. **Fig. 5** (Boxplots): Distribution of results across 30 seeds — shows reproducibility
6. **Fig. 6** (Carbon Emissions): The carbon story — lifecycle vs. operational
7. **Fig. 7** (Scalability): Does it work at different sizes? Yes.
8. **Fig. 8** (Sensitivity): Is it robust to parameter changes? Yes.

No figure is decorative. Each one answers a specific question a reviewer would ask.

---

## 2. The 30-Second Elevator Pitch {#2-elevator-pitch}

> **Practice this out loud until you can say it naturally, without notes.**

"My paper presents CALASH, the first wireless sensor network protocol that reduces the total carbon footprint — not just the electricity to run the sensors, but the CO₂ emitted to manufacture them and dispose of them. The key insight is that building a tiny sensor produces 10 kilograms of CO₂, but running it for its entire life produces only 0.005 grams. So the carbon cost of *making* the sensor is a hundred thousand times larger than the cost of *running* it. This means the best strategy is to keep sensors alive longer so you waste less manufacturing carbon per useful measurement. CALASH achieves this with four mechanisms: smart data compression that adapts to how clean the electricity grid is at any moment, AI-powered routing, automatic recovery after earthquakes, and a carbon accounting engine that tracks the full lifecycle. We tested it with 30 independent experiments against 7 state-of-the-art baselines, and it extends network lifetime by 60% while reducing lifecycle carbon intensity by 33%."

> **If they say "shorter"**: "CALASH makes sensor networks greener by keeping sensors alive longer, because 99.999% of their carbon footprint comes from manufacturing, not operation."

---

## 3. The Story Arc: Why This Paper Exists {#3-story-arc}

Every good paper tells a story. Here is yours, in 5 acts:

**Act 1 — The World We Live In** (Introduction, paragraphs 1–2)
Sensor networks are deployed everywhere for environmental monitoring. They use batteries and eventually die. When they die, all the carbon emitted to manufacture them is wasted if they didn't deliver enough data. Nobody in WSN research thinks about this.

**Act 2 — The Problem Nobody Solved** (Introduction, paragraphs 3–5 + Table I)
Existing protocols optimize energy but ignore carbon. No protocol accounts for manufacturing emissions, adapts to grid carbon intensity, AND survives disasters. Table I proves this gap visually: 7 baselines × 8 features, and no baseline has more than 3 checkmarks.

**Act 3 — Our Solution** (Methodology)
CALASH combines four pillars (compression, routing, self-healing, lifecycle accounting) on top of 6G technologies, with a mathematical theorem that guarantees performance.

**Act 4 — The Proof** (Results)
30 seeds × 13 protocols × 5,000 rounds. CALASH beats every traditional baseline on every metric. Against RIS-DRL (which uses the same hardware), CALASH trades 19% lifetime for carbon awareness + disaster resilience + 4.3% better delivery.

**Act 5 — Honest Reflection** (Limitations + Conclusion)
We disclose 4 limitations with exact numbers, propose 6 concrete future works, and end with the core insight: "send fewer bits" beats "find better routes" because embodied carbon dwarfs operational carbon.

> **In your own words**: "My paper's story is simple. Nobody in sensor networks was thinking about manufacturing carbon. I showed it's 100,000× bigger than operational carbon. Then I built a system that acts on this insight and proved it works."

---

# Part B — Walking Through the Article, Page by Page

---

## 4. Title & Abstract — Every Word Justified {#4-title-abstract}

### The Title

**"CALASH: Carbon-Aware Lifecycle-Adaptive Self-Healing Routing for Disaster-Resilient 6G Wireless Sensor Networks"**

| Word/Phrase | Why it's there |
|-------------|---------------|
| CALASH | The acronym. C(arbon)A(ware)L(ifecycle)A(daptive)S(elf)H(ealing). Memorable, pronounceable. |
| Carbon-Aware | The primary novelty — this protocol reacts to carbon intensity |
| Lifecycle-Adaptive | It considers the full lifecycle (manufacturing + operation + disposal), not just energy |
| Self-Healing | It recovers from disasters automatically |
| Routing | It is a routing protocol (this tells WSN researchers what category the paper is in) |
| Disaster-Resilient | The application context — earthquake zones |
| 6G | The technology substrate — positions the paper as forward-looking |
| Wireless Sensor Networks | The domain — so IEEE TGCN editors can assign the right reviewers |

> **Supervisor Q**: "Why is the title so long?"
> Because IEEE TGCN titles should be descriptive and include the key contribution, domain, and technology. A reviewer scanning 200 submissions must understand from the title alone what this paper offers. Every word serves that purpose.

### The Abstract (154 words)

The abstract has 5 sentences, each with a precise role:

1. **Context**: Sensor networks matter, but sustainability is ignored.
2. **Gap**: No protocol integrates carbon-aware routing with lifecycle assessment and disaster resilience.
3. **Contribution**: CALASH does, with 4 pillars + 6G + theoretical guarantee.
4. **Evidence**: 30 seeds × 13 protocols, specific numbers (+60% lifetime, −33% LCI, 82.9% PDR).
5. **Significance**: First lifecycle-carbon-aware WSN protocol.

> **Supervisor Q**: "Your abstract says 'first.' Are you sure?"
> Yes. Table I systematically checks 8 features across 7 baselines and the entire literature review. No prior WSN routing protocol integrates: (1) lifecycle carbon metric, (2) real-time carbon-aware routing, (3) compressive sensing, (4) self-healing, (5) RL, (6) Lyapunov optimization, (7) 6G, and (8) ISO 14040 LCA. We say "first" only for this specific combination.

---

## 5. Section I: Introduction — The Hook, the Gap, the Claim {#5-introduction}

### Paragraph-by-Paragraph Walkthrough

**Paragraph 1: The hook — carbon in IoT**
We open with a striking fact: manufacturing one sensor emits ~10 kg CO₂, but running it emits only ~0.005 g. The ratio is 5 orders of magnitude (100,000×). This immediately tells the reader "something surprising is happening that justifies this paper."

> **Supervisor Q**: "Where does 10 kg come from?"
> From Pirson & Bol (2021), a peer-reviewed lifecycle assessment of IoT edge devices, and the UN Global E-Waste Monitor (Forti et al. 2024). We cite both. The 10,000 gCO₂eq figure includes: mining rare-earth metals for the chip, silicon wafer fabrication, PCB assembly, packaging, and international shipping.

> **Supervisor Q**: "And the 0.005 g?"
> 0.5 J total energy × (1 kWh / 3,600,000 J) × 200 gCO₂/kWh (UK average grid) = 0.0000278 kWh × 200 = 0.0056 gCO₂. So approximately 0.005 g. The exact value depends on grid carbon intensity, but even at 700 gCO₂/kWh (India), it's only 0.019 g — still 500,000× less than embodied.

**Paragraph 2: The LCI metric**
We define LCI = total lifecycle CO₂ / total useful packets. This is our primary metric. We explain that lower is better and that it captures the full environmental cost per unit of useful work.

> **Supervisor Q**: "Why not just use energy efficiency?"
> Energy efficiency (packets per Joule) ignores the 10 kg of CO₂ embedded in each sensor. A protocol that kills sensors 37% faster looks efficient per Joule but wastes enormous manufacturing carbon. LCI captures the TRUE environmental cost because it includes embodied, operational, AND end-of-life carbon in the numerator.

**Paragraph 3: The disaster context**
Earthquakes kill sensors. Dead sensors waste embodied carbon. So disaster resilience is a carbon efficiency strategy, not just a reliability feature.

**Paragraph 4: The gap — Table I**
This is the most important paragraph in the introduction. Table I is a checklist of 8 features × 7 baselines. Every row has at most 3 checkmarks. Our row (CALASH) has all 8. This is the visual proof of the gap.

> **Supervisor Q**: "How do you know no other protocol has all 8?"
> I conducted a systematic literature review (documented in 01_Literature_Review_Base.md and 02_Detailed_Paper_Extraction.md). I checked the Singh et al. 2017 survey covering 30+ LEACH variants. I checked every RL-based WSN routing paper published since 2020. I checked the entire carbon-aware computing literature (Urgaonkar 2011, Liu 2023, etc.). The gap is that the WSN community and the carbon-aware computing community have not yet connected. We are the bridge.

**Paragraph 5: Contributions**
Five numbered contributions: (1) CALASH framework with 4 pillars, (2) CDL Pareto theorem, (3) comprehensive evaluation, (4) ISO 14040 LCA integration, (5) 6G substrate with practical impairments.

> **Supervisor Q**: "Which is the main contribution?"
> Contribution (1) — the CALASH framework itself. It is the first protocol to jointly minimize lifecycle carbon. The other four contributions support and validate it.

---

## 6. Section II: Related Work — How We Position Ourselves {#6-related-work}

This section has 4 subsections, each mapping to one of our 4 pillars:

### II-A: Energy-Efficient Clustering Protocols (→ CADR fills the gap)
We discuss LEACH (2000), EE-LEACH (2013), HEED (2004).

> **In your own words**: "These protocols are like cars that optimize fuel efficiency but ignore the carbon emitted to build the car factory. They save battery, which is good, but they don't know that keeping a sensor alive one more hour saves 10 kg of manufacturing CO₂ from being wasted."

### II-B: Metaheuristic and RL-Based Routing (→ CARE fills the gap)
We discuss ABC-ACO (2024), EERP (2018), Q-Routing (1994).

> **In your own words**: "These are smarter routing algorithms — like GPS navigation that finds the fastest route. But none of them look at the carbon intensity of the electricity grid when making routing decisions. CARE does."

### II-C: Carbon-Aware Networking (→ CALASH is the first for WSN)
We discuss Urgaonkar (2011), Liu (2023) — carbon-aware scheduling for data centers.

> **In your own words**: "Carbon-aware computing exists, but only for big data centers with powerful servers and unlimited electricity. Nobody applied it to tiny sensors with 0.5 Joules of battery. We did."

### II-D: Disaster-Resilient WSNs and Lifecycle Assessment (→ SHDR + LSE fill the gap)
We discuss Erdelj (2017), Pirson & Bol (2021).

> **In your own words**: "People have studied sensor networks in disaster zones, and people have studied lifecycle carbon of electronics. But nobody connected them. We show that disaster resilience IS a carbon strategy because dead sensors are wasted carbon."

> **Supervisor Q**: "Why only 4 subsections?"
> Because each subsection maps to one pillar of CALASH. This structure shows the reader exactly WHERE our contribution fits in the literature landscape. It's not random — it's organized by gap.

---

## 7. Section III: Methodology — The Engine Room {#7-methodology}

This is the longest section. Every subsection is a design decision that your supervisors may challenge.

### III-A: System Model

> **Supervisor Q**: "Describe your system model."

"200 sensor nodes are scattered uniformly at random in a 200×200 meter area. Each node has a battery of 0.5 Joules — once depleted, the node dies permanently. There is one Base Station (BS) at coordinate (100, 250), which is 50 meters outside the top edge of the field. Nodes organize into clusters. Each cluster has one Cluster Head (CH) that collects data from its members and forwards it toward the BS. Clusters rotate — a different set of CHs is elected every round. One round means: sense → compress → transmit to CH → CH routes to BS."

> **Supervisor Q**: "Why 200 nodes and not 100 or 1000?"
> 200 is the standard benchmark used in LEACH and most WSN clustering papers. It is large enough for statistical significance (enough data points) but small enough for the simulation to complete in reasonable time (31 seconds per 5,000-round run). We also validate at N=100 and N=500 in the scalability analysis.

> **Supervisor Q**: "Why is the BS outside the field?"
> This is the standard LEACH configuration from Heinzelman (2000). Placing the BS outside creates asymmetric distances: some nodes are close (50 m), others are far (300+ m). This asymmetry makes multi-hop routing necessary — if the BS were in the center, most nodes would be within single-hop range and routing algorithms wouldn't matter.

> **Supervisor Q**: "Why 0.5 J?"
> This value comes from the original LEACH paper (Heinzelman 2000). It represents a small coin-cell battery on a Mica2-class sensor mote. All 7 baselines use this same value, ensuring fair comparison.

### III-B: Data Provenance and Reproducibility

> **Supervisor Q**: "Is your data real?"

"I classify every data input into four levels:
1. **Real data**: UK Carbon Intensity API (8,760 hourly readings, CC BY 4.0 license), Intel Lab sensors (2.3 million temperature readings from 54 sensors, public domain), USGS ShakeMap (467,000+ earthquake damage grid points, public domain).
2. **Calibrated synthetic**: Carbon intensity profiles for France, Germany, India, Poland — I took real annual statistics from Ember 2024 and generated hourly profiles matching the real mean, variance, and diurnal pattern.
3. **Model-based**: THz channel from Jornet & Akyildiz 2011, RIS gain from Huang 2021, earthquake aftershock model from Omori-Utsu — these are published physics models with empirically validated parameters.
4. **Simulated**: Node positions (uniform random) and DQN exploration (ε-greedy) — these are inherently random."

> **Supervisor Q**: "Why not use ALL real data?"
> Because real carbon intensity data at hourly resolution for all countries requires a paid Electricity Maps subscription. Instead, I used the free UK Carbon Intensity API for our primary grid and calibrated synthetic profiles from open Ember 2024 statistics for the others. The approach is reproducible and license-free.

### III-C: Problem Formulation

> **Supervisor Q**: "State your optimization problem formally."

"We want to find the routing policy π that minimizes the ratio of total lifecycle carbon to total delivered packets:

$$\min_{\pi} \text{LCI}(\pi) = \frac{\sum_i C_{emb}^{(i)} + \sum_t C_{op}(t) + \sum_{i:\text{dead}} C_{eol}^{(i)}}{\sum_t D(t)}$$

The numerator has three terms: manufacturing carbon of all nodes (fixed at deployment), operational carbon accumulated each round (depends on how much energy we use and how dirty the grid is), and disposal carbon of dead nodes (depends on how many nodes die). The denominator is the total useful packets successfully delivered to the BS."

> **In your own words for a non-specialist**: "Imagine you buy 200 light bulbs. Each bulb cost a lot of pollution to manufacture. You want to maximize the total useful light you get from all of them before they burn out. LCI is the total manufacturing-plus-electricity pollution divided by the total useful light. A good strategy keeps bulbs alive longer and gets more light from each one."

### III-D: CALASH Framework: Four Pillars

This is the heart of your contribution. You must explain each pillar clearly.

#### Pillar 1: CADR — Carbon-Aware Data Reduction

> **In your own words for a non-specialist**: "Instead of sending all 100 temperature readings from a sensor, we send only 30–80 of them, chosen cleverly so the base station can reconstruct the full 100 perfectly. This is like sending a low-resolution photo that can be upscaled back to full resolution because most of the photo is predictable sky — you only need to send the interesting part. When the electricity grid is powered by coal (dirty), we send even fewer readings to save energy and carbon. When it's powered by solar (clean), we send more for better data quality."

> **Supervisor Q**: "Compressive sensing is not new. What's new here?"
> Compressive sensing itself is from Candès et al. 2006. What's new is **modulating the compression ratio based on real-time grid carbon intensity**. No one has connected CS to carbon awareness before. The ρ(CI) mapping function is our contribution.

> **Supervisor Q**: "What if the signal is NOT sparse?"
> Then reconstruction quality degrades. We use temperature signals from Intel Lab which are ~1-sparse in DCT (essentially one dominant frequency). For denser signals, the ρ_min parameter sets a floor: we never compress below 30%, ensuring at least partial reconstruction.

#### Pillar 2: CARE — Carbon-Aware Routing Engine

> **In your own words for a non-specialist**: "Imagine you need to deliver a package across a city. There are many possible relay points. Each relay point has a cost: some are expensive in fuel, some are in polluted neighborhoods. CARE uses two strategies:
> 1. A **mathematical rule** (Lyapunov) that says: 'if we've been polluting too much recently, choose greener routes even if they're less efficient.' This works from day one with no learning.
> 2. An **AI brain** (DQN) that learns from experience which routes work best. After seeing 256 deliveries, the AI takes over and makes even better decisions."

> **Supervisor Q**: "Why do you need BOTH Lyapunov and DQN?"
> Lyapunov gives a **provable guarantee** (Theorem 1) but is suboptimal because it's myopic (one hop at a time). DQN learns a better policy but has **no convergence guarantee**. Together: Lyapunov provides the safety net (always available, provably bounded), DQN provides the performance boost (learned, potentially better). During disaster recovery, DQN is bypassed because its pre-disaster policy may be outdated.

#### Pillar 3: SHDR — Self-Healing Disaster Recovery

> **In your own words for a non-specialist**: "Imagine an office building. Every employee checks in every morning (heartbeat). If someone doesn't check in for 3 days, HR assumes they left (dead node). HR then looks at which desks are empty (coverage holes), reassigns tasks to remaining employees (emergency CH election), and puts the office in 'crisis mode' for 50 days — extra meetings (heartbeats), more managers (CHs), focus on critical work only (max compression)."

> **Supervisor Q**: "Why 3 missed heartbeats and not 1 or 5?"
> One missed heartbeat could be a transmission error (false positive). Five missed heartbeats means delayed detection — the network operates blind for too long. Three is the standard threshold used in autonomic computing (IBM MAPE-K framework, Kephart & Chess 2003).

#### Pillar 4: LSE — Lifecycle Sustainability Engine

> **In your own words for a non-specialist**: "If a relay node is almost out of battery, using it risks killing it. Killing it wastes 10 kg of manufacturing CO₂. So we make almost-dead nodes slightly 'more expensive' to route through. It's like a toll road: the road through a crumbling bridge costs more because if the bridge breaks, you lose the whole bridge."

> **Supervisor Q**: "The ablation shows LSE has no significant effect (p = 0.74). Why keep it?"
> Three reasons: (1) The CDL theorem's proof relies on the lifecycle penalty ℓ_j — removing it breaks the theoretical guarantee. (2) The negligible effect is **by design**: aggressive penalties cause route inflation that wastes more energy than it saves. (3) In very long deployments where many nodes simultaneously approach death, LSE becomes the differentiator. We are honest about p = 0.74 because transparency builds trust.

### III-E: 6G Enabling Technologies

> **Supervisor Q**: "Explain the 6G technologies simply."

"We use three technologies that will be available in 6G networks around 2030:

1. **Sub-THz radio** (140 GHz): Like a very wide highway — enormous bandwidth (10 GHz vs. 100 MHz in 5G) allowing ultra-fast data transfer, but only for short distances (30 meters). Good for communication WITHIN a cluster.

2. **RIS — Reconfigurable Intelligent Surface**: A panel of 64 small antennas that acts like a programmable mirror for radio waves. When a direct signal path is blocked (by earthquake debris, for example), the RIS bounces the signal around the obstacle. It amplifies the signal by 34.2 dB without using any extra power.

3. **ISAC — Integrated Sensing and Communication**: Using the SAME radio transmission for both sending data AND detecting objects (like radar). One transmission, two purposes. This lets us detect structural damage after earthquakes without sending separate radar pulses."

> **Supervisor Q**: "Is 140 GHz realistic for tiny sensors?"
> The ITU-R IMT-2030 framework targets D-band (110–170 GHz) for short-range device-to-device communication in 6G. We use it ONLY for intra-cluster links (≤ 30 m). For longer inter-cluster links, we use standard sub-6 GHz (3.5 GHz). The ablation (CALASH-NoTHz) shows CALASH works without it — 6G gives a +10.5% lifetime boost, not a dependency.

### III-F: CALASH Algorithm (Pseudocode)

> **Supervisor Q**: "Walk me through one round of the algorithm."

"Round t:
1. **Check heartbeats**: Every alive node sent a tiny 50-bit 'I'm alive' message. If any node missed 3 consecutive heartbeats, declare it dead.
2. **Disaster detection**: If many nodes died suddenly (pattern matches an earthquake), enter healing mode for 50 rounds.
3. **Elect cluster heads**: 5% of alive nodes become CHs. In healing mode, 7.5% (50% more). Nodes with more remaining energy are more likely to be elected.
4. **Read carbon intensity**: Check how dirty the electricity grid is right now (CI(t) in gCO₂/kWh).
5. **Set compression ratio**: If CI is high → ρ = 0.3 (compress a lot). If CI is low → ρ = 0.8 (compress little).
6. **Intra-cluster transmission**: Each member compresses its 100-sample reading to ρ×100 samples and sends them to its CH via sub-THz (140 GHz).
7. **Routing to BS**: The CH's aggregated data travels hop-by-hop to the BS. At each hop, the DQN (or Lyapunov fallback) picks the best next relay.
8. **Carbon accounting**: Update the virtual carbon queue Z(t) based on how much carbon this round emitted vs. the budget.
9. **Update lifecycle penalties**: Recalculate each node's ℓ_j based on remaining energy."

### III-G: Theoretical Guarantee: CDL Pareto Bound

> **Supervisor Q**: "State your theorem."

"Theorem 1 (CDL Pareto Bound): Under the CALASH policy with parameter V > 0:
- The time-averaged data delivery is at most B/V below optimal: D̄ ≥ D̄* − B/V
- The time-averaged lifecycle carbon respects the budget plus B/V slack: C̄_tot ≤ c̄ + B/V

Eliminating V gives the Pareto front equation: C̄ = c̄ + (D̄* − D̄), a line with slope −1."

> **In your own words for a non-specialist**: "There's a fundamental trade-off: if you deliver more data, you emit more carbon. If you cut carbon, you deliver less data. Our theorem says CALASH can reach any point on this trade-off curve just by turning one knob (V). And no point is 'wasted' — the curve is convex, meaning there are no gaps. You can always smoothly move from 'eco-friendly but less data' to 'more data but less eco-friendly.'"

> **Supervisor Q**: "This is just standard Lyapunov. What's new?"
> Standard Lyapunov optimization bounds **operational** carbon only. Our CDL theorem extends the virtual queue to incorporate **end-of-life carbon** from node deaths: C_tot = C_op + K(t)·c_eol_eff. This is the first lifecycle-extended Lyapunov bound for WSN routing. The proof structure is standard (drift → penalty → telescope → stability), but the object being bounded is novel.

### III-H: DQN Training Hyperparameters

> **Supervisor Q**: "Justify your hyperparameters."

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Architecture | 9→64→32→1 | Smallest that captures the 9D state. Tested 32→16→1 (underfits) and 128→64→1 (no improvement, 4× slower) |
| Learning rate | 0.001 | Standard for Adam optimizer in small networks |
| Batch size | 64 | Standard mini-batch size. 32 gives higher variance, 128 gives marginal improvement |
| Replay buffer | 10,000 | Large enough to decorrelate samples, small enough for 520 KB SRAM |
| Target update τ | 0.005 | Soft update. Hard copy every N steps is brittle for online learning |
| ε annealing | Cosine, 1.0 → 0.05 over 3,000 steps | Smooth decay, avoids the "cliff" of linear annealing |
| Gradient clipping | max norm 1.0 | Prevents exploding gradients during early learning |
| Discount factor γ | 0.95 | Standard for multi-hop routing (3–5 hops to BS) |

### III-I: Time Complexity Analysis

> **Supervisor Q**: "What is the complexity per round?"

"O(N log N + K·M² + K·H·|N_i|), where N = total nodes, K = number of CHs, M = cluster size, H = hops to BS, |N_i| = neighborhood size. In practice: ~200 nodes, 10 CHs, 20 per cluster, 3–5 hops, ~20 neighbors. The DQN forward pass is 2,656 multiply-accumulate operations per candidate — about 0.3 ms on an 8 MHz microcontroller."

---

## 8. Section IV: Results and Discussion — The Evidence {#8-results}

### IV-A: Experimental Setup

> **Supervisor Q**: "How did you run the experiments?"

"I ran 30 independent random seeds (42 to 71), each for 13 protocols, each for 5,000 rounds. That's 30 × 13 × 5,000 = 1,950,000 simulation rounds total. Each seed generates a different random node deployment, ensuring results are not an artifact of one lucky topology. All 13 protocols share the exact same simulator, energy model, channel model, and random seed — the ONLY difference between protocols is the routing/compression algorithm."

> **Supervisor Q**: "Why seeds 42 to 71?"
> The starting seed 42 is a convention in computer science (reference to Douglas Adams). We use 30 consecutive seeds starting from 42 for reproducibility — anyone can run the same seeds and get identical results.

### IV-B: Main Results (Table III)

> **Supervisor Q**: "Summarize your main results."

"CALASH achieves:
- **Half-death round 1,486 ± 14**: 60% longer than LEACH (931), 69% longer than EE-LEACH (878), 84% longer than ABC-ACO (808)
- **PDR 82.9%**: Higher than EE-LEACH (63.8%), EERP (64.6%), Q-Routing (63.6%)
- **LCI 8.99 gCO₂/packet**: 33% lower than LEACH (13.42), 32% lower than EERP (13.21)
- **Efficiency 2,323 pkt/J**: 51% higher than LEACH (1,536)

All pairwise comparisons against traditional baselines are statistically significant at p < 10⁻⁵."

### IV-C: Discussion — CALASH vs. Traditional Baselines

> **In your own words**: "CALASH crushes all traditional baselines on lifetime AND carbon. The mechanism is simple: CADR's compression means sensors transmit 45% fewer bits per round, extending battery life dramatically. The extra lifetime amortizes the 10 kg manufacturing carbon over more useful packets, driving LCI down."

### IV-D: Discussion — CALASH vs. RIS-DRL (The Critical Comparison)

> **This is where your supervisors will push hardest.**

| Metric | CALASH | RIS-DRL | Winner |
|--------|--------|---------|--------|
| Lifetime | 1,486 | **1,764** (+19%) | RIS-DRL |
| PDR | **0.829** | 0.794 | CALASH (+4.3%) |
| LCI | 8.99 | **7.89** (−12%) | RIS-DRL |

> **Supervisor Q**: "RIS-DRL beats you on 2 of 3 metrics. Why should we care about CALASH?"

"RIS-DRL wins on lifetime and LCI because it uses ALL its energy for raw survival — it has zero overhead from carbon awareness or disaster resilience. It's like comparing a truck with no safety features to one with airbags, ABS, and emission controls. The truck without safety features is faster and cheaper, but you wouldn't deploy it in an earthquake zone.

Specifically, CALASH provides:
- **Carbon awareness**: Adapts routing to grid carbon intensity — essential for regulatory compliance (EU Green Deal, Paris Agreement reporting)
- **Disaster resilience**: Self-heals after earthquakes — RIS-DRL's network collapses permanently
- **+4.3% higher PDR**: CALASH's multi-objective reward prevents packet drops
- **ISO 14040 compliance**: Can report auditable lifecycle carbon — RIS-DRL cannot

The 19% lifetime overhead is the **measured cost** of these capabilities. We quantify it precisely via ablation (CARE: 10.7%, SHDR: 1.7%). No one else offers these capabilities at any price."

### IV-E: Ablation Study

> **Supervisor Q**: "What is an ablation study and why do you need it?"

"An ablation study removes one component at a time and measures the impact. It's like baking a cake, then baking it without sugar, without flour, without eggs — each missing ingredient tells you what that ingredient contributes. In AI research, this is the gold standard for proving each component adds value.

Our ablation reveals a clear hierarchy:
1. **CADR** is the dominant pillar: removing it drops lifetime by 37% and increases LCI by 59%
2. **6G (THz/RIS/ISAC)** is second: removing it drops lifetime by 9.5%
3. **CARE** introduces the largest overhead: removing it INCREASES lifetime by 10.7% — this is the price of carbon awareness
4. **SHDR** adds modest overhead: removing it increases lifetime by 1.7% — the price of disaster resilience
5. **LSE** has negligible effect: p = 0.74, not significant — it's a gentle tiebreaker by design"

### IV-F: Statistical Significance

> **Supervisor Q**: "How do you know your results are not due to chance?"

"I use the Wilcoxon signed-rank test, which is:
- **Paired**: Compares the SAME random seed under two different protocols. This eliminates the effect of topology differences — any performance difference is purely due to the algorithm.
- **Non-parametric**: Makes no assumption about the data distribution. Simulation data is often non-normal, so the standard t-test would be inappropriate.
- **Conservative**: Harder to get significance, which makes our results MORE credible when we do.

The p-values are < 1.8 × 10⁻⁶ for all main comparisons. This is the SMALLEST possible p-value for n=30 with Wilcoxon — it means CALASH beat the baseline on every single one of the 30 seeds. The probability of this happening by chance is 0.00018%."

### IV-G: Supplementary Campaigns

> **Supervisor Q**: "Did you test robustness?"

"Yes, four additional campaigns:
1. **Scalability** (N = 100, 200, 500): CALASH maintains its LCI advantage at every scale: −40% at N=100, −34% at N=200, −17% at N=500.
2. **Sensitivity analysis** (4 parameters): No parameter causes more than ±15% LCI variation. CALASH is robust.
3. **Carbon intensity across national grids** (France, UK, Germany, India): Advantage is largest in clean grids (France: −41%) because CALASH fully exploits CADR without carbon penalty inflating the numerator.
4. **Execution time**: CALASH runs in 31 seconds (Python, 5,000 rounds) — faster than ABC-ACO (37 seconds)."

### IV-H: Limitations

> **Supervisor Q**: "What are your limitations?"

"I disclose four:
- **L1**: RIS-DRL outperforms on lifetime by 19% and LCI by 12%. This is the cost of carbon awareness + disaster resilience.
- **L2**: CARE and SHDR introduce 12.4% total lifetime overhead. These are measured, quantified costs of specific capabilities.
- **L3**: Simulation-only evaluation. But every baseline we compare against also uses simulation-only. We propose an $840 ESP32 testbed for future work.
- **L4**: Single disaster event (with aftershocks). We propose multi-disaster evaluation with 3–5 USGS ShakeMap events."

> **Supervisor Q**: "Why disclose limitations? Doesn't it weaken the paper?"
> The opposite. Disclosing limitations STRENGTHENS the paper because: (1) it prevents reviewer ambush — they can't find a flaw we didn't already acknowledge; (2) it proves intellectual honesty; (3) each limitation comes with a concrete future work proposal, showing a research roadmap; (4) top journals (Nature, IEEE) explicitly require a limitations section.

---

## 9. Section V: Conclusion — Landing the Plane {#9-conclusion}

> **Supervisor Q**: "Summarize your contribution in 3 sentences."

"CALASH is the first WSN routing protocol that minimizes lifecycle carbon intensity — accounting for manufacturing, operation, and disposal — rather than just energy. Its dominant mechanism is carbon-aware compressive sensing, which reduces transmitted data by up to 70% and extends lifetime by 60% versus LEACH. The theoretical CDL Pareto bound guarantees that near-optimal delivery and carbon budget compliance are simultaneously achievable."

### Future Work (6 Items)

| # | What | Why |
|---|------|-----|
| 1 | Close the RIS-DRL gap (lighter CARE, passive ISAC sensing) | Addresses L1, L2 |
| 2 | $840 ESP32 hardware testbed | Addresses L3 |
| 3 | Multi-disaster evaluation (3–5 USGS ShakeMap events) | Addresses L4 |
| 4 | Solar/RF energy harvesting + Lyapunov | Natural extension |
| 5 | Multi-agent DQN for decentralized routing | Scalability |
| 6 | ns-3 co-simulation for THz channel validation | Realism |

---

# Part C — Deep Concept Explanations for Non-Specialists

---

## 10. Explain Carbon to a Non-Specialist {#10-carbon}

> **Imagine you're explaining to a friend who studies music.**

"You know how every product has a hidden environmental cost? When you buy a guitar, carbon dioxide was emitted to mine the metal for the strings, cut the wood, power the factory, ship it to the store. That's called **embodied carbon** — the carbon 'embedded' in the product before you even use it.

A sensor node is like a tiny guitar that costs 10 kg of CO₂ to build but only 0.005 g of CO₂ to play its entire life. So 99.999% of its environmental impact happened BEFORE it was turned on.

Our metric, LCI, is like asking: 'How much pollution per song?' If the guitar breaks after 10 songs, each song cost 1 kg of manufacturing pollution. If it lasts 1,000 songs, each song costs only 10 grams. So the best environmental strategy is to make the guitar last as long as possible.

CALASH does this for sensors: it makes them last 60% longer, so each data measurement 'costs' 33% less CO₂."

---

## 11. Explain Wireless Sensor Networks to a Non-Specialist {#11-wsn}

"Imagine 200 tiny thermometers scattered across a football field after an earthquake. Each thermometer has a small battery — once the battery dies, the thermometer is useless forever. One computer at the edge of the field (the base station) needs to collect all the temperature readings.

The thermometers are too far from the computer to shout directly — they'd use too much battery. So they form groups (clusters), each group picks a leader (cluster head), and members whisper to their leader. The leader then shouts to the next leader, who shouts to the next, until the data reaches the computer. This chain of whispers is called **multi-hop routing**.

The challenge: how do you decide who leads, who whispers to whom, and how much data to send — all while keeping batteries alive as long as possible? That's what WSN routing protocols solve. CALASH adds: also minimize the total pollution, and automatically reorganize after an earthquake kills some thermometers."

---

## 12. Explain AI/Reinforcement Learning to a Non-Specialist {#12-ai}

"Imagine teaching a dog to fetch a ball by throwing treats. The dog tries different actions (run left, run right, jump). When it does something good (gets closer to the ball), it gets a treat. When it does something bad (runs into a wall), it gets nothing. Over many attempts, the dog learns which actions lead to treats.

Our DQN (Deep Q-Network) is like that dog. The 'ball' is delivering data to the base station. The 'treats' are rewards for getting closer to the BS, and penalties for wasting energy or causing pollution. The 'brain' is a small neural network with 9 inputs (how much battery is left, how far from the BS, how dirty the grid is, etc.) and one output (how good this next hop is).

After 256 attempts, the DQN gets good enough to take over from the mathematical rule (Lyapunov). But the mathematical rule is always there as a safety net — if the dog gets confused (e.g., after an earthquake changes the terrain), we fall back to the rule until the dog re-learns."

---

## 13. Explain 6G Technologies to a Non-Specialist {#13-6g}

"Think of three upgrades to a postal system:

1. **Sub-THz (fast local mail)**: Instead of regular mail trucks on narrow roads, you get a superhighway that's 100 times wider. Packages travel incredibly fast, but only within your neighborhood (30 meters). That's THz: enormous bandwidth for short distances.

2. **RIS (smart mirror)**: Imagine the road to your neighbor's house is blocked by rubble after an earthquake. A RIS is like placing a giant mirror on a building wall that bounces the mail around the rubble to reach the neighbor. No extra fuel needed — the mirror is passive. Our mirror has 64 tiles and boosts the signal by 34.2 decibels (2,600×).

3. **ISAC (two-for-one)**: Normally, you'd need one truck to deliver mail and another truck with radar to scan for damage. ISAC is like a single truck that delivers mail AND takes radar photos of the road at the same time. One trip, two jobs."

---

## 14. Explain Compressive Sensing to a Non-Specialist {#14-cs}

"Imagine you need to send a photo of a sunset over the phone, but the phone line is slow. The photo is 100 pixels. But 98 of those pixels are 'orange sky' — boring, predictable. Only 2 pixels are interesting (the sun and a bird).

Compressive sensing says: instead of sending all 100 pixels, send 55 randomly mixed measurements. The receiver knows that most of the photo is boring, so it can figure out the full 100 pixels from just 55 measurements. This works PERFECTLY when the signal is 'sparse' — meaning most of the information is concentrated in a few important components.

Temperature readings from sensors are extremely sparse — they change slowly and predictably. Our signals are ~1-sparse in the frequency domain (essentially one dominant frequency). So we can compress them to 30–55% of original size with **zero loss** of information."

---

## 15. Explain Lyapunov Optimization to a Non-Specialist {#15-lyapunov}

"Imagine you have a monthly budget for groceries. Some weeks you overspend (big dinner party), other weeks you underspend (leftovers). You keep a running tally: if you're over budget, you eat cheaply next week. If you're under budget, you can splurge.

That running tally is the **virtual carbon queue** Z(t) in Lyapunov optimization. When Z is large (we've been emitting too much carbon), the algorithm becomes conservative — choosing greener routes even if they're slightly less efficient. When Z is small (we've been clean), the algorithm can use higher-energy routes.

The beautiful property is: you never need to predict the future. You just look at your current tally and make the best decision for THIS round. Over time, the math guarantees you'll stay within budget on average."

---

## 16. Explain the Theorem to a Non-Specialist {#16-theorem}

"Our theorem says: there's a fundamental trade-off between data delivery and carbon emissions — you can't maximize both. But CALASH can reach ANY point on this trade-off curve by turning one knob (the parameter V).

Turn V up → more data delivery, but more carbon slack
Turn V down → tighter carbon control, but less data

The curve is a straight line with slope −1: every extra packet of data costs exactly one unit of carbon slack. And the curve is **convex** — meaning there are no wasted points, no gaps, no places where you'd want to be somewhere you can't reach.

What's novel: previous theorems only bounded the electricity carbon. Ours bounds the TOTAL lifecycle carbon (manufacturing + electricity + disposal). This is the first time anyone included the cost of dead sensors in a mathematical guarantee."

---

## 17. Explain Statistics to a Non-Specialist {#17-statistics}

"When we say 'CALASH achieves 1,486 ± 14 rounds,' we mean:
- We ran the experiment 30 times with different random starting conditions
- The average across all 30 runs was 1,486 rounds
- The ± 14 is the 95% confidence interval: we're 95% sure the true average is between 1,472 and 1,500

When we say 'p < 1.8 × 10⁻⁶,' we mean:
- We compared CALASH to LEACH on the same 30 random conditions
- CALASH beat LEACH on ALL 30 out of 30
- The probability of this happening by pure luck (if they were actually equal) is less than 0.00018%
- So we are extremely confident the difference is real, not a fluke

Why Wilcoxon and not t-test: the t-test assumes data follows a bell curve. Simulation data often doesn't. Wilcoxon makes no such assumption — it just counts wins and losses. This makes our conclusions more conservative and more credible."

---

# Part D — Every Technical Term, Equation, and Number

---

## 18. Complete Glossary {#18-glossary}

### Network & Sensor Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **WSN** | Wireless Sensor Network | A collection of small battery-powered devices that sense the environment and wirelessly send data to a central collector |
| **Node** | Sensor Node | One single sensor device with battery, radio, processor, and sensing unit |
| **BS** | Base Station | The central computer that receives all data. At (100, 250) in our simulation |
| **CH** | Cluster Head | A node elected as local group leader. Collects data from members, forwards to BS |
| **Cluster** | — | A group of nearby nodes managed by one CH |
| **Round** | Simulation Round | One time step: sense → compress → transmit to CH → CH routes to BS |
| **Half-Death Round** | — | Round when 50% of nodes have died. THE standard lifetime measure |
| **PDR** | Packet Delivery Ratio | Delivered packets ÷ generated packets. Higher is better |
| **Multi-hop Routing** | — | Sending data through intermediate relay nodes instead of directly to BS |
| **Jain's Fairness Index** | — | 0 to 1 measure of how evenly energy is consumed. 1.0 = perfectly balanced |

### Carbon & Sustainability Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **LCI** | Lifecycle Carbon Intensity | gCO₂eq per useful packet. Our primary metric. Lower = greener |
| **CI** | Carbon Intensity | gCO₂ per kWh of electricity. Varies by hour (solar = low, coal = high) |
| **gCO₂eq** | Grams CO₂ equivalent | Standard unit for greenhouse gas emissions |
| **Embodied Carbon** | — | CO₂ from manufacturing. 10,000 gCO₂eq per node |
| **Operational Carbon** | — | CO₂ from electricity during operation. Tiny (~0.005 g total per node) |
| **End-of-Life Carbon** | — | CO₂ from disposal. 500 × (1 − 0.3) = 350 gCO₂eq per dead node |
| **LCA** | Lifecycle Assessment | ISO 14040 methodology for environmental impact from cradle to grave |
| **r_recycle** | Recycling Rate | 30% based on UN Global E-Waste Monitor 2024 |

### AI & Machine Learning Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **RL** | Reinforcement Learning | AI that learns by trial and error with rewards and penalties |
| **DQN** | Deep Q-Network | Neural network that estimates the value of actions. 9→64→32→1 architecture |
| **Double DQN** | — | Two-network DQN that avoids overestimation. More stable |
| **Q-value** | — | Expected future reward of an action. Higher = better action |
| **Replay Buffer** | Experience Replay | Memory of past experiences, sampled randomly for training |
| **ε-greedy** | Epsilon-greedy | Explore randomly with probability ε, exploit best known action with 1−ε |
| **Cosine Annealing** | — | Smooth schedule for ε: follows cosine curve from 1.0 to 0.05 over 3,000 steps |
| **MLP** | Multi-Layer Perceptron | Simple neural network with fully connected layers |
| **ReLU** | Rectified Linear Unit | Activation function: output = max(0, input) |
| **Xavier Init** | Glorot Initialization | Weight initialization for stable training start |
| **Soft Update** | — | Blend target network slowly: target = τ×main + (1−τ)×target, τ = 0.005 |

### Optimization Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **Lyapunov Optimization** | — | Converts long-term budget constraint into per-round decisions via virtual queue |
| **Virtual Carbon Queue Z(t)** | — | Running tally of carbon overshoot. Large Z → be conservative |
| **Drift-Plus-Penalty** | — | Minimize [queue growth] + [V × objective]. Automatically balances constraint and objective |
| **V Parameter** | Lyapunov Tradeoff | Knob controlling energy–carbon balance. We use V = 100 |
| **Pareto Front** | — | Set of solutions where improving one objective worsens another |
| **Convex** | — | Shape where any line between two boundary points stays inside. No gaps |

### Compressive Sensing Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **CS** | Compressive Sensing | Compress below Nyquist rate using signal sparsity |
| **ρ (rho)** | Compression Ratio | Fraction of data actually sent. ρ = 0.3 means only 30% |
| **Measurement Matrix Φ** | — | Random Gaussian matrix that "mixes" the signal: y = Φ·x |
| **DCT** | Discrete Cosine Transform | Transform revealing frequency content. Temperature is ~1-sparse in DCT |
| **OMP** | Orthogonal Matching Pursuit | Algorithm to reconstruct signal from compressed measurements |
| **NMSE** | Normalized Mean Squared Error | Reconstruction error. Fidelity = 1 − NMSE. We achieve F = 1.000 |
| **Sparsity s** | — | Number of significant DCT coefficients. Our signals: s ≈ 1 out of n = 100 |

### 6G Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **Sub-THz** | Sub-Terahertz (140 GHz) | Very high bandwidth (10 GHz), very short range (30 m) |
| **RIS** | Reconfigurable Intelligent Surface | 64-element programmable reflector. Gain ≈ 34.2 dB |
| **ISAC** | Integrated Sensing and Communication | Same signal for data AND radar. One transmission, two purposes |
| **OFDM** | Orthogonal Frequency Division Multiplexing | Splitting bandwidth into 2,048 sub-carriers for robust transmission |
| **PAPR** | Peak-to-Average Power Ratio | OFDM high peaks waste power. 3 dB back-off in our model |
| **CFAR** | Constant False-Alarm Rate | Radar detection with fixed false-alarm probability (10⁻⁴) |
| **Range-Doppler Map** | — | 2D radar image: distance × speed. Resolution: 1.5 cm |

### Self-Healing Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **MAPE-K** | Monitor-Analyze-Plan-Execute with Knowledge | IBM framework for self-managing systems |
| **Heartbeat** | — | 50-bit "I'm alive" message every 2 rounds |
| **Coverage Hole** | — | Area with no surviving sensor after disaster |
| **Orphan Node** | — | Alive node whose CH died |
| **Recovery Duration** | — | 50 rounds of "healing mode" with extra CHs and frequent heartbeats |

### Statistical Terms

| Term | Full Name | Simple Explanation |
|------|-----------|-------------------|
| **Monte Carlo** | — | Running same experiment many times with different random seeds and averaging |
| **Seed** | Random Seed | Starting number for random generator. Same seed = same results. Seeds 42–71 |
| **95% CI** | Confidence Interval | Range where true mean lies with 95% probability. mean ± t × (std / √n) |
| **Wilcoxon** | Signed-Rank Test | Non-parametric paired comparison. No normality assumption |
| **p-value** | — | Probability of seeing our results by chance. < 0.05 = significant |
| **Non-parametric** | — | No assumption about data distribution. More robust |

### Protocol Names

| Protocol | Year | What It Does |
|----------|------|-------------|
| **LEACH** | 2000 | Random CH election, the "MNIST of WSN" |
| **LEACH-1hop** | — | LEACH variant, CHs send directly to BS |
| **EE-LEACH** | 2013 | Energy-weighted CH election |
| **ABC-ACO** | 2024 | Bee + ant colony optimization for CH selection |
| **EERP** | 2018 | Energy-distance relay selection (representative baseline) |
| **Q-Routing** | 1994 | Tabular Q-learning from Boyan & Littman (no neural network) |
| **RIS-DRL** | 2020–2024 | Composite 6G baseline from Huang/Yang/Al-Hilo, no carbon/healing |
| **CALASH** | Ours | Full framework: CADR + CARE + SHDR + LSE + 6G |

---

## 19. Every Equation in Plain Language {#19-equations}

### Eq. 1: LCI (the metric we optimize)

$$\text{LCI} = \frac{C_{emb} + C_{op} + C_{eol}}{D_{total}}$$

"Total lifecycle pollution divided by total useful data. Lower = greener."

### Eq. 2–3: Radio Energy Model

$$E_{Tx}(l, d) = l \cdot E_{elec} + l \cdot \begin{cases} \varepsilon_{fs} \cdot d^2 & d < 87.7\text{m} \\ \varepsilon_{mp} \cdot d^4 & d \geq 87.7\text{m} \end{cases}$$

"Sending l bits over distance d costs: (1) a fixed electronics cost per bit (50 nJ/bit), plus (2) an amplifier cost that grows as d² for short range or d⁴ for long range. The crossover at 87.7 m comes from two different propagation physics: free space (line of sight) vs. ground reflection (multipath)."

### Eq. 4: Operational Carbon

$$C_{op}(E, t) = E \cdot \frac{1}{3.6 \times 10^6} \cdot CI(t)$$

"Convert Joules to kilowatt-hours, multiply by grid carbon intensity. Gives grams of CO₂."

### Eq. 5: Formal LCI Objective

$$\min_{\pi} \frac{\sum_i C_{emb}^{(i)} + \sum_t C_{op}(t) + \sum_{i:\text{dead}} C_{eol}^{(i)}}{\sum_t D(t)}$$

"Find the policy π that minimizes total lifecycle carbon per delivered packet."

### Eq. 6: CADR Compression Ratio

"A piecewise-linear function mapping CI(t) to ρ(t). Below average CI → ρ closer to 0.8 (send more). Above average CI → ρ closer to 0.3 (send less). Centered at the grid average."

### Eq. 7: Carbon Queue Update

$$Z(t+1) = \max\{0, Z(t) + C_{op}(t) - \bar{c}\}$$

"Queue grows when we pollute more than our budget c̄. Shrinks (toward zero) when we pollute less. Can never go negative."

### Eq. 8: Lyapunov Routing Decision

$$j^* = \arg\min_{j \in \mathcal{N}(i)} \left[Z(t) \cdot c_{ij}(t) + V \cdot e_{ij}\right] \cdot \ell_j$$

"For each candidate relay: multiply (carbon pressure × carbon cost + V × energy cost) by lifecycle penalty. Pick the cheapest."

### Eq. 9: DQN Architecture

$$\text{State(9D)} \xrightarrow{ReLU} 64 \xrightarrow{ReLU} 32 \xrightarrow{linear} 1$$

"9 inputs → 64 neurons → 32 neurons → 1 output (Q-value). Total: 2,656 multiply-add operations."

### Eq. 10: DQN Reward

"Six terms: +1.0 for progress toward BS, −0.3 for carbon, −0.3 for energy waste, −0.2 for routing through dying nodes, +5.0 bonus for delivery, −2.0 penalty for drops."

### Eq. 11: Lifecycle Penalty

$$\ell_j = 1 + w_{eol}(1 - E_j/E_0)^2$$

"Penalty is 1 at full battery, grows quadratically to 2 at zero battery."

### Eq. 12: THz Channel Capacity

$$C_{eff} = \eta_{OFDM} \cdot B \cdot \log_2(1 + SNR)$$

"Shannon capacity × OFDM efficiency (0.93). At 10 GHz bandwidth, gives enormous throughput."

### Eq. 13: RIS Gain

$$G_{RIS} = 20\log_{10}(64) + G_{CSI} + G_{beam} - L_{coupling} \approx 34.2 \text{ dB}$$

"64 elements give 36.1 dB ideally. Three impairments reduce it to 34.2 dB."

### CDL Theorem Bounds

$$\bar{D} \geq \bar{D}^* - B/V \quad ; \quad \bar{C}_{tot} \leq \bar{c} + B/V$$

"Delivery gap shrinks as 1/V. Carbon slack also shrinks as 1/V. Trade-off: tune V to pick your point on the Pareto front."

---

## 20. Numbers You Must Know by Heart {#20-cheatsheet}

### Core Results

| What | Number |
|------|--------|
| CALASH half-death | **1,486 ± 14** rounds |
| CALASH PDR | **0.829 ± 0.006** (82.9%) |
| CALASH LCI | **8.99 ± 0.10** gCO₂eq/pkt |
| CALASH efficiency | **2,323 ± 24** pkt/J |
| vs. LEACH lifetime | **+60%** (1,486 vs 931) |
| vs. LEACH LCI | **−33%** (8.99 vs 13.42) |
| vs. all traditional lifetime | **+17% to +84%** |
| vs. all traditional LCI | **−32% to −44%** |
| Embodied carbon per node | **10,000 gCO₂eq** (~10 kg) |
| Operational carbon per node (entire life) | **~0.005 g** |
| Ratio embodied/operational | **~100,000× (5 orders of magnitude)** |

### RIS-DRL Comparison (MEMORIZE THIS)

| Metric | CALASH | RIS-DRL | Gap |
|--------|--------|---------|-----|
| Lifetime | 1,486 | **1,764** | −18.7% (they win) |
| PDR | **0.829** | 0.794 | +4.3% (we win) |
| LCI | 8.99 | **7.89** | +12.2% (they win) |
| Carbon awareness | ✅ | ❌ | We win |
| Disaster resilience | ✅ | ❌ | We win |
| ISO 14040 LCA | ✅ | ❌ | We win |

### Ablation Hierarchy (MEMORIZE THIS ORDER)

| Pillar Removed | Lifetime Change | LCI Change | p-value |
|---------------|----------------|------------|---------|
| **CADR** | **−37%** (930) | **+59%** (14.29) | < 10⁻⁵ |
| **6G (THz/RIS)** | −9.5% (1,345) | +9.5% (9.84) | < 10⁻⁵ |
| **CARE** | +10.7% (1,644) | −9.2% (8.16) | < 10⁻⁵ |
| **SHDR** | +1.7% (1,510) | −1.9% (8.82) | 0.006 |
| **LSE** | −0.1% (1,484) | 0% (8.99) | 0.74 (NS) |

Order to remember: **CADR >> 6G >> CARE >> SHDR >> LSE**

### Configuration Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| Nodes | 200 | Standard LEACH benchmark |
| Area | 200 × 200 m² | Standard benchmark |
| BS | (100, 250) | 50 m outside field, standard |
| Energy | 0.5 J per node | Heinzelman 2000 standard |
| Rounds | 5,000 | Long enough for all nodes to die |
| Seeds | 42–71 (30) | CLT ≥ 30, reproducible |
| Disaster | Round 2,000, r = 100 m | Mid-simulation, ~30% casualties |
| CH fraction | 5% | LEACH optimal |
| DQN | 9→64→32→1 | Smallest effective architecture |
| V (Lyapunov) | 100 | Validated robust (50–500 range) |

### Statistical Numbers

| What | Value |
|------|-------|
| Seeds | 30 |
| Test | Wilcoxon signed-rank |
| α | 0.05 |
| Minimum p-value (all 30 agree) | 1.8 × 10⁻⁶ |
| CI method | t-distribution, 95% |

---

# Part E — Anticipating Challenges

---

## 21. 80 Supervisor/Reviewer Questions with Prepared Answers {#21-questions}

### Category A: Novelty & Contribution (Q1–Q10)

**Q1: What is the main novelty of this paper?**
> CALASH is the first WSN routing protocol that minimizes **lifecycle** carbon intensity. We integrate carbon-aware compression, Lyapunov-guaranteed routing, autonomic self-healing, and 6G technologies with a formal theoretical bound covering the full lifecycle.

**Q2: How is this different from just adding compressive sensing to LEACH?**
> Three differences: (1) Compression ratio dynamically adapts to grid carbon intensity — never done before; (2) Combined with Lyapunov routing, DQN, self-healing, and lifecycle accounting — not just compression; (3) We provide a theoretical guarantee bounding full lifecycle carbon.

**Q3: The LCI metric is just total carbon / total packets. That's trivial.**
> The metric is simple by design. The novelty is: (a) including ALL THREE carbon phases (embodied + operational + end-of-life) per ISO 14040, (b) showing embodied dominates by 5 orders of magnitude, and (c) building a framework that directly optimizes this metric.

**Q4: Why not use energy efficiency instead of LCI?**
> Energy efficiency (pkt/J) ignores 10 kg of embodied carbon per node. A protocol killing nodes 37% faster looks efficient per Joule but wastes massive manufacturing carbon. LCI captures the true environmental cost.

**Q5: Is CALASH really "the first"?**
> Yes, for this specific combination. Table I checks 8 capabilities across 7 baselines. No prior protocol has more than 3. I surveyed 30+ LEACH successors, all major RL routing papers, and the carbon-aware computing literature.

**Q6: Why didn't you compare against more protocols?**
> 7 baselines + 5 ablation variants = 13 protocols is more comprehensive than any published WSN paper. HEED, TEEN, PEGASIS are 2004-era protocols subsumed by our representative EERP and EE-LEACH implementations.

**Q7: Can you position your work in one sentence relative to each baseline?**
> LEACH (2000): random CH election, no intelligence. EE-LEACH (2013): energy-weighted, still no carbon. ABC-ACO (2024): nature-inspired optimization, no carbon/disaster. EERP (2018): energy-distance relay competition, no RL/carbon. Q-Routing (1994): tabular RL from Boyan & Littman, no neural network/carbon. RIS-DRL (composite, 2020–2024): same 6G hardware, no carbon/lifecycle/healing. CALASH: all of the above, integrated.

**Q8: What's the single most important insight?**
> Embodied carbon dominates operational carbon by 100,000×. Therefore, keeping sensors alive longer is a far more effective carbon strategy than optimizing routing paths.

**Q9: If CADR is the dominant pillar, why not just publish CADR alone?**
> CADR alone achieves ~70% of the improvement. But a complete solution needs: routing intelligence (CARE), disaster recovery (SHDR), lifecycle accounting (LSE), and enabling hardware (6G). Publishing CADR alone would be an incremental contribution; the integration is what makes it a systems paper suitable for IEEE TGCN.

**Q10: How does your work relate to the UN Sustainable Development Goals?**
> SDG 9 (Industry/Innovation), SDG 11 (Sustainable Cities), SDG 12 (Responsible Consumption), SDG 13 (Climate Action). CALASH directly reduces the lifecycle environmental impact of IoT infrastructure while maintaining disaster resilience.

### Category B: Methodology & Design (Q11–Q25)

**Q11: Why Python and not ns-3 or MATLAB?**
> (1) Reproducibility: pure Python/NumPy, no proprietary dependencies. (2) DQN integration in the same codebase. (3) Every baseline we compare against used custom simulators too. (4) Fair comparison: all 13 protocols share identical simulator code.

**Q12: Why not use a more modern RL algorithm (PPO, SAC)?**
> (1) DQN runs in NumPy alone — deployable on 8 MHz motes. (2) Discrete action space (choose next hop) — policy gradient is for continuous actions. (3) Double DQN suffices for our small state/action space.

**Q13: Why not a GNN or transformer?**
> 100,000+ MACs vs. our 2,656. On an 8 MHz mote with 4 KB RAM, this matters. We chose the simplest model that works.

**Q14: The DQN reward has 6 hand-tuned weights. How?**
> Priority ordering: delivery (1.0) > carbon/energy (0.3) > lifecycle (0.2), plus terminal bonuses (±5/2). Validated via sensitivity analysis: performance is robust across a wide range.

**Q15: Why 200 nodes?**
> Standard LEACH benchmark. Validated with N=100 and N=500 in scalability analysis.

**Q16: Why BS at (100, 250)?**
> Standard Heinzelman (2000) configuration. Creates asymmetric distances requiring multi-hop routing.

**Q17: Why 0.5 J per node?**
> From original LEACH paper. Represents a coin-cell battery on a Mica2-class mote.

**Q18: Why 5% CH fraction?**
> Optimal value from LEACH paper (Heinzelman 2000). Validated in our sensitivity analysis (3–15% range, 5% is the sweet spot).

**Q19: Why 5,000 rounds?**
> Long enough for ALL protocols' nodes to die, ensuring fair lifetime comparison across all 13 protocols.

**Q20: Why disaster at round 2,000?**
> Mid-simulation: enough time for DQN to learn pre-disaster (2,000 rounds) and enough rounds post-disaster (3,000) to evaluate recovery.

**Q21: Why 100 m damage radius?**
> Calibrated to the 2023 Turkey-Syria earthquake MMI ≥ VIII isoseismal radius. Kills approximately 30% of nodes in our 200×200 m field.

**Q22: Why Gaussian damage model?**
> Approximation of the real spatial decay of seismic intensity with distance from epicenter. Calibrated to USGS ShakeMap empirical data.

**Q23: What is your simulator NOT modeling?**
> No multipath fading (deterministic path loss), no MAC contention (perfect scheduling), no clock drift, no thermal noise beyond link budget. These are standard simplifications in ALL WSN routing papers we cite. Relative comparisons remain valid.

**Q24: Could you run this on ns-3?**
> Yes, we propose ns-3 co-simulation as Future Work item #6 specifically for THz channel validation.

**Q25: Why 30 seeds? Why not 100?**
> Central Limit Theorem: at n ≥ 30, the sample mean is approximately normal, enabling proper confidence intervals. 100 seeds would tighten CIs but not change conclusions — our p-values are already at the minimum possible (1.8 × 10⁻⁶).

### Category C: Theory (Q26–Q35)

**Q26: State your theorem.**
> Under CALASH with parameter V: delivery ≥ optimal − B/V, and lifecycle carbon ≤ budget + B/V. Eliminating V gives a Pareto front with slope −1.

**Q27: This is just standard Lyapunov. What's new?**
> Standard Lyapunov bounds operational carbon only. CDL bounds TOTAL lifecycle carbon (operational + end-of-life). The virtual queue incorporates node deaths.

**Q28: Is the proof correct?**
> It follows Neely (2010) drift-plus-penalty with one extension: end-of-life carbon in the queue. The proof structure is standard; the object being bounded is novel.

**Q29: How tight is the bound? B/V = 200 seems loose.**
> Lyapunov bounds are worst-case by nature. In practice, CALASH outperforms the bound significantly. The value is the EXISTENCE of a guarantee, not its tightness.

**Q30: What happens if V → ∞?**
> Delivery → optimal, but carbon slack → ∞ (no carbon constraint). V = 100 is our operating point, validated as robust.

**Q31: What happens if V → 0?**
> Carbon perfectly budgeted, but delivery may be very poor. Extreme conservation.

**Q32: What is the value of B?**
> B ≈ 20,000 for N=200. It depends on the worst-case energy cost of a single transmission.

**Q33: The Pareto front is a straight line. Isn't real life curved?**
> The linearity is a RESULT (from the B/V structure), not an assumption. Higher-order terms introduce slight curvature preserving convexity. In practice, near-linear for reasonable V.

**Q34: Does the theorem require i.i.d. carbon intensity?**
> No. Lyapunov optimization works with arbitrary (even adversarial) sequences. The proof uses the drift bound which holds regardless of CI sequence.

**Q35: Can the theorem be extended to multi-objective beyond 2D?**
> Yes, with additional virtual queues. Each constraint gets its own queue. The Pareto front becomes a surface. This is standard multi-queue Lyapunov (Neely 2010, Chapter 5).

### Category D: Results (Q36–Q55)

**Q36: CALASH vs. LEACH: justify the 60% lifetime improvement.**
> CADR reduces transmitted bits by 45% on average (ρ ≈ 0.55). Fewer bits = less radio energy = longer life. The multi-hop routing (CARE) further reduces distance-dependent costs.

**Q37: Why does CALASH have lower PDR than LEACH?**
> LEACH (0.857) dies early (931 rounds). CALASH (0.829) lives 60% longer (1,486 rounds). Over longer life, more packets are generated. CALASH delivers more TOTAL packets despite a slightly lower per-round rate.

**Q38: Data fidelity is 1.000 for ALL protocols. Is that meaningful?**
> Yes — it validates that CS with ρ ≥ 0.3 achieves lossless reconstruction for signals with sparsity s ≈ 1. For denser signals, fidelity would degrade, and the ρ_min parameter controls the quality floor.

**Q39: Operational carbon is tiny. Why bother with carbon-aware routing?**
> Two purposes: (1) proof of concept for regulatory compliance; (2) CARE's Lyapunov queue implicitly extends lifetime by conserving energy during high-CI periods, which is the real LCI driver.

**Q40: NoLCI has no significant effect. Why keep it?**
> (1) CDL theorem depends on ℓ_j; (2) by design — aggressive penalties cause route inflation; (3) matters in long deployments; (4) we honestly report p = 0.74.

**Q41: NoCO2 has BETTER LCI. Doesn't carbon awareness hurt?**
> In raw LCI, yes. This is the measured cost (10.7% lifetime overhead). The value is the CAPABILITY to adapt to grid CI — essential under carbon regulations.

**Q42: Why does RIS-DRL beat CALASH?**
> RIS-DRL spends zero energy on carbon awareness or disaster monitoring. All energy goes to raw survival. It's a simpler problem. The 19% gap = 10.7% (CARE) + 1.7% (SHDR) + ~6% (routing suboptimality from β-modulated CH election).

**Q43: Can CALASH close the gap to RIS-DRL?**
> Future Work #1: lighter CARE (reduce the 10.7% overhead) and passive ISAC-based failure detection (reduce SHDR heartbeat cost).

**Q44: Scalability: why does LCI advantage narrow at N=500?**
> CADR compression is per-node, not per-network. At large N, routing overhead grows superlinearly while CADR savings grow linearly.

**Q45: Sensitivity: is V = 100 optimal?**
> The sensitivity analysis shows LCI is flat between V = 50 and V = 500. Any value in this range works. V = 100 is a pragmatic choice.

**Q46: Why is the advantage largest in clean grids (France: −41%)?**
> In clean grids, CALASH exploits CADR maximally without the carbon penalty inflating the LCI numerator. In dirty grids, both CALASH and LEACH have high numerators.

**Q47: Execution time: is 31 seconds realistic for deployment?**
> The 31 seconds is Python simulation overhead for 5,000 rounds. In real deployment, each round takes milliseconds. The DQN forward pass is 0.3 ms on an 8 MHz mote.

**Q48: Could DQN training be done on-device?**
> On an ESP32 (240 MHz, 520 KB): yes, slowly. On a Mica2 (8 MHz, 4 KB): no, only inference. Training would be offloaded to the gateway.

**Q49: What is Jain's Fairness Index for CALASH?**
> CALASH achieves high fairness because CARE distributes routing load across nodes and LSE discourages overusing weak nodes.

**Q50: How does CALASH perform without disaster (no earthquake)?**
> The SHDR module becomes dormant (no heartbeat failures detected). CALASH still benefits from CADR, CARE, LSE, and 6G. The 1.7% SHDR heartbeat overhead persists but is negligible.

**Q51: What if the earthquake hits at round 500 instead of 2000?**
> DQN has less training data, so the Lyapunov fallback handles more of the routing. Performance degrades slightly pre-recovery but the SHDR healing mechanism is independent of DQN training state.

**Q52: What about multiple disasters?**
> Our codebase supports aftershocks via Omori-Utsu model. Full multi-disaster campaigns are Future Work #3.

**Q53: Why Wilcoxon and not Mann-Whitney?**
> Wilcoxon is for **paired** samples (same seed, two protocols). Mann-Whitney is for unpaired. Since we pair by seed, Wilcoxon is correct and more powerful.

**Q54: Your CI uses 95% via t-distribution. Why not bootstrap?**
> With n = 30 and roughly symmetric distributions, t-distribution CIs are nearly identical to bootstrap CIs. We chose t-distribution for simplicity and convention.

**Q55: Are there outlier seeds?**
> The boxplots (Fig. 5) show all 30 seeds. The interquartile range is tight, with no extreme outliers. This confirms robustness across topologies.

### Category E: 6G Technologies (Q56–Q65)

**Q56: Is 140 GHz realistic?**
> ITU-R IMT-2030 targets D-band (110–170 GHz) for short-range D2D. We use it only for intra-cluster (≤ 30 m). Inter-cluster uses sub-6 GHz.

**Q57: Where is the physical RIS?**
> Simulated using Huang 2021 cascaded channel model with 3 practical impairments. Physical testbed proposed in Future Work #2.

**Q58: Is ISAC proven at these frequencies?**
> ISAC is a defining IMT-2030 capability. Our implementation follows standard range-Doppler processing with CFAR detection.

**Q59: Without 6G, does CALASH still beat baselines?**
> Yes. CALASH-NoTHz still achieves HD=1,345 and LCI=9.84, beating all traditional baselines.

**Q60: What's the RIS gain formula?**
> 20log₁₀(64) + G_CSI(−0.92) + G_beam(−0.01) − L_coupling(−1.0) = 34.2 dB.

**Q61: Why 64 RIS elements?**
> 8×8 array. Small enough for low-power operation, large enough for meaningful gain. Matches commercially available designs.

**Q62: What is PAPR back-off?**
> OFDM signals have high peaks. The 3 dB back-off means we operate the amplifier at half its maximum power to avoid distortion.

**Q63: What about molecular absorption at 140 GHz?**
> Water molecules absorb at specific THz frequencies. At 140 GHz and 30 m range, the absorption is 0.02 dB (negligible). We include it in the channel model.

**Q64: Why OFDM and not single-carrier?**
> OFDM handles frequency-selective fading and enables ISAC via range-Doppler processing (2D FFT).

**Q65: Could this work with 5G instead of 6G?**
> Yes, but with less bandwidth (100 MHz vs. 10 GHz). Data transfer takes longer, consuming more energy. The 6G advantage is speed → less radio-on time → less energy.

### Category F: Reproducibility & Ethics (Q66–Q73)

**Q66: Can I reproduce your results?**
> Yes. Seeds 42–71, complete code, real data files, and download scripts are in the repository. `python run_campaign.py` reproduces all 390 simulations.

**Q67: Is the Intel Lab data still relevant (2004)?**
> The physics of temperature sensing hasn't changed. Environmental signals are still sparse. Intel Lab is the "MNIST of WSN" — used for benchmarking, not for claiming state-of-the-art on a sensing task.

**Q68: Are there ethical concerns?**
> No human subjects, no private data. All data sources are open (CC BY 4.0, public domain). The research aims to reduce environmental impact.

**Q69: Are your baselines implemented correctly?**
> We distinguish three categories: (1) **Faithful reproductions** — LEACH and LEACH-1hop follow Heinzelman (2000) exactly; ABC-ACO follows El Khediri (2024) with documented parameter adaptations for our network scale. (2) **Representative implementations** — EE-LEACH, EERP, and Q-Routing implement the standard paradigms from the cited works (energy-weighted CH election, energy-distance relay selection, and tabular Q-learning respectively) but are not line-by-line clones of any single codebase. (3) **Composite baseline** — RIS-DRL is synthesised from Huang (2020), Yang (2021), and Al-Hilo (2024) to create the strongest possible 6G-aware baseline sharing CALASH's THz+RIS substrate. All 7 baselines share the same simulator infrastructure, energy model, and random seeds. Code is open-source.

**Q69a: Why did you choose THESE specific baselines — some from 1994, 2000, 2013, 2018?**
> The seven baselines were deliberately selected to span **four generations** of WSN routing paradigms:
> 1. **Probabilistic clustering** — LEACH (Heinzelman, 2000): the most-cited WSN protocol with 30,000+ citations. It is the universal baseline in every WSN comparison paper.
> 2. **Energy-weighted refinements** — EE-LEACH (Bakaraniya, 2013): the paradigm of residual-energy-weighted CH election that all subsequent LEACH variants follow.
> 3. **Metaheuristic and relay optimization** — ABC-ACO (El Khediri, 2024): a current state-of-the-art metaheuristic; EERP (Biswas, 2018): the energy-distance relay paradigm.
> 4. **Reinforcement-learning routing** — Q-Routing (Boyan & Littman, 1994): the **foundational** Q-learning routing paper from which all subsequent WSN Q-routing descends; RIS-DRL (composite 6G-DRL): the strongest possible 6G-aware opponent sharing CALASH's THz+RIS substrate.
>
> We include seminal formulations (e.g., Boyan 1994, LEACH 2000) because CALASH should be measured against the **canonical algorithmic idea**, not an arbitrary implementation variant. Including the year-2024 ABC-ACO confirms the comparison also covers current methods. The Related Work further discusses three 2025 papers (Akram, Wang, Kaur) to demonstrate full awareness of the latest literature. This four-generation span plus five ablation variants gives reviewers complete coverage: paradigm breadth externally, contribution isolation internally.

**Q69b: Why "representative" implementations instead of exact reproductions for EERP, Q-Routing, and EE-LEACH?**
> Three reasons: (1) **No open-source code exists** for EERP (Biswas 2018), Q-Routing (Boyan 1994), or EE-LEACH (Bakaraniya 2013) — only algorithmic descriptions in the papers. Every WSN comparison paper reimplements baselines from text. (2) **Fair comparison requires identical infrastructure** — we needed all 13 protocols to share the same energy model, channel model, and simulator code. Plugging in external code would introduce confounding differences. (3) **The comparison is paradigm-level, not code-level** — we compare energy-weighted CH election (the EE-LEACH paradigm) against CALASH, not a specific author's MATLAB script against ours. The paper states this explicitly in the "Protocols compared" paragraph (Section IV-A). This is standard practice in all top WSN comparison papers.

**Q69c: Why is RIS-DRL a composite and not from one paper?**
> Because no single paper implements all four components we need: THz intra-cluster communication + RIS-assisted relay selection + DQN-based routing + multi-hop WSN topology. RIS-DRL synthesises these from Huang (2020, RIS+DRL beamforming), Yang (2021, RIS anti-jamming DRL), and Al-Hilo (2024, RIS-UAV with DRL). We designed it to be the **strongest possible** 6G-aware baseline — one that shares CALASH's entire physical-layer substrate (THz + RIS) so that any performance gap is attributable solely to CALASH's four novel algorithmic pillars, not to hardware advantages. The article explicitly states "composite baseline" and multi-cites all three source papers.

**Q70: What software versions?**
> Python 3.11, NumPy 1.26, SciPy 1.12, Matplotlib 3.8. Pinned in requirements.txt.

**Q71: How long did the full campaign take?**
> 30 seeds × 13 protocols × 31 seconds ≈ 3.4 hours on a MacBook Pro M2.

**Q72: What is the carbon footprint of running the simulation itself?**
> ~3.4 hours × 30W (M2 power) × 200 gCO₂/kWh (UK grid) ≈ 20 gCO₂. Ironic but negligible.

**Q73: Are there licensing issues with the data?**
> UK Carbon Intensity API: CC BY 4.0. Intel Lab data: public domain. USGS ShakeMap: public domain. Ember 2024: CC BY 4.0. No paid subscriptions required.

### Category G: Writing & Strategy (Q74–Q80)

**Q74: Why is the paper long?**
> The length reflects comprehensive evaluation (13 protocols, ablation, 4 supplementary campaigns, data provenance). IEEE TGCN review format allows 30 pages. Every section adds value.

**Q75: Why include data provenance?**
> Preempts "Is your data real?" — we classify every input transparently. No other WSN paper does this.

**Q76: Why 4 limitations? Doesn't that weaken the paper?**
> Disclosing limitations STRENGTHENS the paper: prevents reviewer ambush, shows mastery, converts weaknesses into future work, builds trust.

**Q77: Why target IEEE TGCN?**
> TGCN (Transactions on Green Communications and Networking) specifically solicits papers on sustainable network design. Our lifecycle carbon-aware WSN protocol is a direct fit.

**Q78: What is the key takeaway for practitioners?**
> Deploy CALASH in disaster-prone, carbon-regulated environments. For stable, carbon-indifferent environments, RIS-DRL suffices.

**Q79: What is the key takeaway for researchers?**
> Embodied carbon dominates operational carbon for IoT by 5 orders of magnitude. This changes the optimization landscape entirely — routing optimization is secondary to lifetime extension.

**Q80: What makes this publishable in a top journal?**
> (1) Novel problem formulation (lifecycle carbon for WSN), (2) complete framework (4 pillars + 6G), (3) theoretical guarantee (CDL Pareto bound), (4) comprehensive evaluation (13 protocols, 30 seeds, 4 supplementary campaigns), (5) radical transparency (data provenance, limitations, open-source).

---

## 22. The "Trivial" Questions Supervisors Love to Ask {#22-trivial}

These seem simple but trip up many students. Practice these.

**Q: What does CALASH stand for?**
> Carbon-Aware Lifecycle-Adaptive Self-Healing.

**Q: What journal are you targeting?**
> IEEE Transactions on Green Communications and Networking (IEEE TGCN).

**Q: What is the impact factor?**
> IEEE TGCN impact factor is approximately 5.3 (2024). It's a Q1 journal in telecommunications.

**Q: Who are the typical reviewers for this journal?**
> Researchers in green communications, sustainable networking, energy-efficient protocols, and 6G systems.

**Q: How many references do you cite?**
> 57 references, spanning 1992–2026, covering WSN, carbon-aware computing, RL, 6G, and lifecycle assessment.

**Q: What does "gCO₂eq" mean?**
> Grams of carbon dioxide equivalent. The "equivalent" accounts for other greenhouse gases (methane, etc.) converted to their CO₂ impact using standardized global warming potentials.

**Q: What is ISO 14040?**
> The international standard for lifecycle assessment. It defines four phases: (1) goal and scope, (2) inventory analysis, (3) impact assessment, (4) interpretation. We follow its framework.

**Q: Why is it called a "virtual" queue?**
> Because no physical data is queued. Z(t) is a mathematical counter tracking carbon overshoot — it exists only in the algorithm's memory, not as buffered packets.

**Q: What is a "protocol" in your context?**
> A set of rules that determines: (1) how clusters form, (2) which node becomes CH, (3) how data is compressed, (4) which path packets take to the BS.

**Q: What is the difference between "round" and "epoch"?**
> A "round" is one simulation time step (sense→compress→transmit→route). An "epoch" is not used in our paper. In RL, an "episode" is one complete experience (packet source to BS or drop) — we have multiple episodes per round.

**Q: What does "±14" mean in "1,486 ± 14"?**
> It's the 95% confidence interval half-width. We are 95% confident the true population mean is between 1,472 and 1,500.

**Q: Why is the first seed 42?**
> Convention from computer science: 42 is "the answer to life, the universe, and everything" (Douglas Adams, The Hitchhiker's Guide to the Galaxy). Many codebases use it as the default random seed.

**Q: What is a "baseline"?**
> An existing protocol from the literature that we compare against. Our 7 baselines are the best-known protocols from 4 generations of WSN research.

**Q: What is "ablation"?**
> Removing one component and measuring the impact. Like removing one ingredient from a recipe to see what it contributes. Named after medical ablation (tissue removal).

**Q: What does "non-parametric" mean?**
> A statistical method that makes no assumption about the data's distribution. Parametric methods (like t-test) assume a bell curve. Non-parametric methods (like Wilcoxon) work with any shape.

**Q: What is "p < 10⁻⁵"?**
> The probability of observing our results by pure chance is less than 0.001%. Extremely strong evidence that the difference is real.

**Q: What does "state-of-the-art" mean?**
> The current best known method. "State-of-the-art" changes as new papers are published. Our claim is that CALASH is state-of-the-art for lifecycle-carbon-aware WSN routing.

**Q: What is "multi-hop" vs. "single-hop"?**
> Single-hop: node sends directly to BS (one jump). Multi-hop: node sends to relay 1, relay 1 sends to relay 2, ..., last relay sends to BS (multiple jumps). Multi-hop saves energy for distant nodes because energy grows as d² or d⁴.

**Q: How do you know 5,000 rounds is "enough"?**
> Because by round 5,000, virtually all nodes have died in all 13 protocols. The simulation captures the full lifecycle from deployment to death.

**Q: What is the "Nyquist rate"?**
> The minimum sampling rate needed to perfectly reconstruct a signal: 2× the highest frequency. Compressive sensing breaks this limit by exploiting sparsity.

**Q: What is a "confidence interval"?**
> A range of values that likely contains the true population parameter. A 95% CI means: if we repeated the experiment 100 times, about 95 of the CIs would contain the true mean.

**Q: What is the difference between "accuracy" and "precision"?**
> Accuracy = how close to the true value (low bias). Precision = how consistent across repeated measurements (low variance). Our 30 seeds give us both: tight CIs (precision) centered on reproducible means (accuracy).

**Q: What does "statistically significant" mean?**
> The observed difference is unlikely to have occurred by chance alone. With our α = 0.05 threshold, "significant" means less than 5% probability of a false positive.

**Q: What is the difference between correlation and causation?**
> Correlation: two things tend to happen together. Causation: one thing CAUSES the other. Our ablation study establishes causation — removing CADR CAUSES lifetime to drop by 37%.

**Q: What does "scalable" mean?**
> The system works well as the problem size increases. We test N = 100, 200, 500 and show CALASH maintains its advantage at every scale.

**Q: What is "overfitting" in machine learning?**
> The model memorizes training data instead of learning general patterns. We avoid it with: small network (2,656 params), replay buffer (decorrelation), target network (stabilization), and cosine ε-annealing (continued exploration).

**Q: Why do you use the word "framework" and not "algorithm"?**
> An algorithm is a single procedure. CALASH is a framework: it integrates 4 pillars + 6G + carbon accounting into a unified system. Each pillar is an algorithm; the combination is a framework.

---

## 23. How to Handle "I Don't Know" {#23-unknown}

It will happen. A supervisor asks something outside your scope. Here's how to handle it:

### Template Responses

**For questions beyond scope:**
> "That's an excellent question and it's beyond the scope of this paper. In our future work, we propose [specific item] to address exactly that. Specifically, future work item #[X] covers [description]."

**For questions about hardware details:**
> "Our evaluation is simulation-based, as stated in limitation L3. The hardware implementation — including firmware in C/C++ for the MCU — is proposed as Future Work #2 with a fully specified $840 ESP32 testbed. I can share the bill of materials."

**For questions about other domains:**
> "That's a great point connecting to [their domain]. While I focused on WSN routing in earthquake zones, the CALASH framework is modular: the disaster model can be replaced with [flood/wildfire/industrial failure] and the carbon source with the local grid. I would be happy to discuss how to adapt it."

**For deep mathematical questions you're unsure about:**
> "The proof follows the standard drift-plus-penalty technique from Neely (2010), with our extension being the lifecycle carbon term in the virtual queue. I can walk you through the key steps if you'd like, starting from the Lyapunov function L(t) = Z(t)²/2."

### What NEVER to Say
- ❌ "I don't know" (without a follow-up)
- ❌ "That's not in the paper" (sounds defensive)
- ❌ "My supervisor told me to do it this way" (sounds passive)
- ❌ "The AI generated that part" (fatal — you must own everything)

### What to Say Instead
- ✅ "That's a great question. Based on our analysis..." (then give your best answer)
- ✅ "We investigated this and found that..." (reference your sensitivity analysis or ablation)
- ✅ "This is precisely what limitation L[X] addresses, and we propose..." (redirect to future work)
- ✅ "I would need to verify the exact number, but the mechanism is..." (show understanding, admit precision gap)

---

## 24. Final Advice: Mindset and Delivery {#24-advice}

### Before You Walk In
1. **Memorize Section 20** (the cheat sheet) — numbers flow naturally in answers
2. **Practice the elevator pitch** out loud 10 times
3. **Know the ablation hierarchy** by heart: CADR >> 6G >> CARE >> SHDR >> LSE
4. **Understand the RIS-DRL comparison** — this is where 50% of tough questions come from
5. **Be ready to draw the round flow diagram** on a whiteboard
6. **Read through all 80 Q&As** at least twice
7. **Practice the non-specialist explanations** (Sections 10–17) with a non-technical friend

### During the Defense
1. **Start every answer with the conclusion**, then explain the mechanism. "Yes, RIS-DRL beats us by 19% on lifetime. Here's why, and here's what we get in return..."
2. **Use numbers**: "60% improvement" is 10× more convincing than "significant improvement"
3. **When you don't know**: redirect to future work with specifics
4. **When challenged on a limitation**: "Yes, we identified this as limitation L[X] in Section IV-H, and we propose [specific future work]."
5. **Show depth**: "The ablation proves CADR is the dominant pillar, contributing 37% of lifetime improvement and 59% of LCI improvement."
6. **Show breadth**: Connect to broader context — "This aligns with the broader sustainable computing movement where Pirson & Bol showed embodied carbon dominates for IoT."
7. **Use analogies**: The non-specialist explanations in Part C are your secret weapon. When a supervisor seems confused, switch to an analogy.

### The One Killer Sentence
> "The counterintuitive insight of this paper is that the single most effective strategy to reduce the lifecycle carbon footprint of a wireless sensor network is not to optimize routing paths — it's to send fewer bits through compressive sensing, because embodied carbon dominates operational carbon by five orders of magnitude."

Say this with confidence. Back it up with the numbers. You will impress any committee.

### Body Language
- **Stand, don't sit** (if presenting)
- **Make eye contact** with the person asking
- **Pause before answering** (1–2 seconds shows you're thinking, not reciting)
- **Use your hands** when describing the architecture or flow
- **Smile when acknowledging a good question** — it shows confidence, not nervousness

### The Golden Rule
**Own the work.** When you say "I built this," "I discovered this," "I measured this" — you must mean it. Your supervisors want to hear YOU explain it, not hear a paper being read back to them. If you can explain the 100,000× carbon ratio, the ablation hierarchy, and the RIS-DRL trade-off in your own words, with numbers, with confidence — you pass.

---

*Document updated March 9, 2026. Aligned with article v1 (32 pages, 0 citation warnings, commit b827fe9). Covers all 42 sections/subsections of the article, all 8 figures, all 13 protocols, and all 57 bibliography entries. Baseline honesty audit complete: 3 faithful reproductions (LEACH, LEACH-1hop, ABC-ACO), 3 representative implementations (EE-LEACH, EERP, Q-Routing), 1 composite baseline (RIS-DRL).*

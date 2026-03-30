# 🛡️ DEEP DEFENSE GUIDE — Article 1: GAPF (Graph-Attentive Policy Fusion)

> **Purpose**: This document is your ultimate preparation guide for a brutal, in-depth oral defense. Every concept, equation, number, and design choice is explained as if you were teaching a bachelor student who has never seen reinforcement learning or graph neural networks. If you understand this document, no question can surprise you.

---

## Table of Contents

1. [The Big Picture — What Problem Are We Solving?](#1-the-big-picture)
2. [Background Concepts You Must Master](#2-background-concepts)
3. [The Problem Formulation — Every Detail](#3-problem-formulation)
4. [The Energy Model — Line by Line](#4-energy-model)
5. [The Reward System — The Monotonic Q·K Attention Network](#5-reward-system)
6. [GAPF Architecture — Every Layer, Every Parameter](#6-gapf-architecture)
7. [Training Procedure — How Everything Learns](#7-training-procedure)
8. [Time Complexity — Why GAPF Doesn't Cost More](#8-time-complexity)
9. [Results — Know Every Number](#9-results)
10. [Deployment Feasibility — From PyTorch to Microcontroller](#10-deployment)
11. [Limitations — Be Honest Before They Ask](#11-limitations)
12. [Likely Brutal Questions and How to Answer Them](#12-brutal-questions)

---

## 1. The Big Picture

### 1.1 The Real-World Problem

**Disasters are devastating**: According to the European Environment Agency (EEA), a disaster is "a serious disruption of the functioning of society, causing widespread human, material or environmental losses, which exceed the ability of affected society to cope using only its own resources" *(EEA Glossary)*. In 2023 alone, 398 natural disasters were recorded *(Statista, 2023)* with 95,000 deaths and losses of around $380 billion *(Burgueño Salas, Statista, 2023)*. Monitoring these disasters (earthquakes, floods, wildfires) requires sensors deployed in the field that collect data and send it back to a central base station.

**Wireless Sensor Networks (WSNs)**: These are collections of small, battery-powered sensors scattered in a disaster zone *(Al Qundus et al., 2020)*. Each sensor measures something (temperature, vibration, smoke) and must relay its data to a Base Station (BS) through other sensors — this is called **multi-hop routing** *(Yarali, 2020)*.

**The core tension**: 
- Sensors run on batteries → you want to **minimize energy consumption**
- In a disaster, data must arrive quickly → you need **low latency**
- If one sensor dies (battery empty), you lose coverage → you need **energy balance**
- All sensor readings must reach the BS → you need **high Packet Delivery Ratio (PDR)**

These goals **conflict**: delivering more packets burns more energy. Balancing energy across all sensors requires longer, less direct routes. This is the fundamental tension our work resolves.

### 1.2 Why Existing Solutions Fall Short

| Approach | Problem | Source |
|----------|----------|--------|
| Classical metaheuristics (PSO, Firefly, Dragonfly) | Static node assumption, no adaptation, cluster-head bottlenecks | *(Biabani et al., 2020; Hosseinzadeh et al., 2022; Chaurasia et al., 2023)* |
| Single RL (Q-learning) | Reward function is a simple weighted sum that can't capture multi-objective complexity | *(Su et al., 2023)* |
| QMIX | Theoretically limited — only captures monotonic value decomposition | *(Ding et al., 2022; MARL Textbook, MIT Press 2024)* |
| QTRAN | Theoretically more principled, but practically harder to train | *(Son et al., 2019)* |
| All of the above | Ignore the spatial graph topology of the sensor network | *Our observation* |

### 1.3 Our Solution in One Paragraph

We propose **GAPF (Graph-Attentive Policy Fusion)**, a lightweight meta-learning framework. The idea: instead of building one giant RL algorithm, we train two experts (QMIX and QTRAN) independently, freeze them, and then train a tiny meta-controller (only 1,473 parameters!) via **REINFORCE** *(Williams, 1992)* that looks at the **topology** of the sensor network (who is connected to whom) and decides which expert to use for each deployment. The topology is encoded using a **Graph Convolutional Network (GCN)**. The reward function used to train the experts is itself learned through a **Monotonic Attention Network** optimized by **Evolution Strategies**. This creates a bi-level optimization: the inner loop trains the RL agents, the outer loop shapes the reward.

---

## 2. Background Concepts You Must Master

### 2.1 Reinforcement Learning (RL) — The Basics

**What is RL?** An agent interacts with an environment. At each step:
1. The agent **observes** the current state
2. It takes an **action**
3. The environment gives a **reward** and transitions to a new state
4. The agent learns to maximize cumulative reward over time

**Q-value**: $Q(s, a)$ is the expected total future reward if you are in state $s$, take action $a$, and then follow the best strategy forever. The agent learns to pick $a^* = \arg\max_a Q(s, a)$.

**Policy gradient (REINFORCE)** *(Williams, 1992)*: Instead of learning Q-values, learn a policy $\pi_\theta(a|s)$ directly. Update parameters by:
$$\nabla_\theta J = \mathbb{E}\left[(G - b) \nabla_\theta \log \pi_\theta(a|s)\right]$$
where $G$ is the total return and $b$ is a baseline to reduce variance.

### 2.2 Multi-Agent RL (MARL)

In our problem, **each sensor is an agent**. They all act simultaneously. The challenge: each sensor only sees its local observation (its own energy, position, packets), but the outcome depends on what ALL sensors do.

**Dec-POMDP (Decentralized Partially Observable Markov Decision Process)** *(MARL Textbook, MIT Press 2024)*: The formal framework. Each agent $i$ gets a partial observation $o_i$, takes action $a_i$, and the team gets a shared reward. The agents must cooperate despite only seeing their own local information.

### 2.3 CTDE (Centralized Training, Decentralized Execution)

**The golden paradigm** *(Kraemer & Banerjee, 2016; Lowe et al., 2017)*: During training (on a powerful server), agents can share information and use centralized modules (mixers, replay buffers). At deployment (on tiny sensor nodes), each agent runs independently using only its local network — a small GRU. The mixer, reward network, and training infrastructure are **thrown away**.

> ⚠️ **KEY DEFENSE POINT**: If they ask "how can this run on a sensor?", the answer is: the sensor only runs the lightweight GRU agent (~100 KB). All the complex stuff (QMIX mixer, QTRAN constraints, attention network, ES loop) only existed during training on a server and is discarded.

### 2.4 QMIX — What It Is and Why It's Limited

**QMIX** *(described in Ding et al., 2022; MARL Textbook, MIT Press 2024)* learns individual Q-values $Q_i(o_i, a_i)$ for each agent. Then a **mixing network** combines them:
$$Q_{tot} = f_{mix}(Q_1, Q_2, \ldots, Q_N; s)$$

The constraint: the mixing network has **non-negative weights**, which guarantees:
$$\frac{\partial Q_{tot}}{\partial Q_i} \geq 0$$

This means: if agent $i$'s action improves its individual Q-value, it also improves the team's total Q-value. This is the **monotonicity constraint**.

**Why is QMIX limited?** It can only represent value functions where $\arg\max_a Q_{tot} = (\arg\max_{a_1} Q_1, \ldots, \arg\max_{a_N} Q_N)$. In other words, greedy individual actions must equal the greedy joint action. This fails for some coordination tasks where agents must sacrifice individual benefit for team benefit.

### 2.5 QTRAN — Theoretically Better, Practically Harder

**QTRAN** *(Son et al., 2019)* addresses QMIX's limitation. It learns:
- Individual Q-values $Q_i(o_i, a_i)$
- A joint Q-value $Q_{jt}(s, \mathbf{a})$
- A value function $V_{jt}(s)$

It enforces two constraints:
1. **Optimality constraint**: $\sum_i Q_i(o_i, a_i^*) - Q_{jt}(s, \mathbf{a}^*) + V_{jt}(s) = 0$ (at optimal actions)
2. **Non-optimality constraint**: $\sum_i Q_i(o_i, a_i) - Q_{jt}(s, \mathbf{a}) + V_{jt}(s) \geq 0$ (at other actions)

**In theory**: QTRAN can represent any monotonic value decomposition (a superset of QMIX).  
**In practice**: The constraints are hard to enforce, leading to instability. That's why QMIX often works just as well empirically.

> ⚠️ **KEY DEFENSE POINT**: In our experiments, QMIX and QTRAN produce nearly identical results (within 1-2% PDR). This validates GAPF's design — the benefit comes from topology-aware selection, not from one expert being universally better.

### 2.6 Graph Convolutional Networks (GCN)

**Intuition** *(Kipf & Welling, ICLR 2017)*: A GCN is a neural network that operates on graphs. Each node updates its representation by aggregating information from its neighbors. After multiple layers, each node's representation encodes not just its own features, but the structure of its local neighborhood.

**Formally** *(Kipf & Welling, 2017)*: Given adjacency matrix $\mathbf{A}$ and node features $\mathbf{X}$:
1. Add self-loops: $\tilde{\mathbf{A}} = \mathbf{A} + \mathbf{I}$ (each node also looks at itself)
2. Normalize: $\hat{\mathbf{A}} = \tilde{\mathbf{D}}^{-1/2} \tilde{\mathbf{A}} \tilde{\mathbf{D}}^{-1/2}$ where $\tilde{D}_{ii} = \sum_j \tilde{A}_{ij}$
3. One layer: $\mathbf{H} = \sigma(\hat{\mathbf{A}} \mathbf{X} \mathbf{W})$

**Why symmetric normalization?** Without it, nodes with many neighbors would have disproportionately large feature values. The $\tilde{\mathbf{D}}^{-1/2}$ on each side ensures that each node's aggregated representation is properly scaled, regardless of its degree.

### 2.7 Evolution Strategies (ES)

**What is ES?** *(Salimans et al., 2017)* A gradient-free optimization method. Instead of computing gradients, you:
1. Perturb parameters randomly: $\phi' = \phi + \sigma \varepsilon$, where $\varepsilon \sim \mathcal{N}(0, I)$
2. Evaluate the perturbed parameters (run an episode)
3. Use the result to estimate the gradient direction

**Why use ES instead of backpropagation?** Because the reward function parameters $\phi$ affect the RL training process, which runs for a full episode. Differentiating through an entire RL episode is extremely expensive and unstable. ES is simple, parallelizable, and doesn't require differentiability.

---

## 3. Problem Formulation

### 3.1 The Sensor Model

Each of the $N$ sensors $S_k$ is defined by:
$$S_k = \begin{cases} \text{CoverageRadius}_k = R & \text{(same for all sensors)} \\ \text{Position}_k = (x_k, y_k) & \text{(2D coordinates)} \\ \text{RemainingEnergy}_k = RE_k & \text{(starts at } E_0 = 1 \text{ J)} \\ \text{ConsumptionEnergy}_k = CE_k & \text{(accumulated energy spent)} \\ \text{NumberOfPackets}_k = N_k & \text{(starts at 1)} \end{cases}$$

### 3.2 The Communication Graph

Two sensors $i$ and $j$ can communicate if and only if:
$$\|p_i - p_j\|_2 \leq R$$

This creates an undirected graph. The adjacency matrix is:
$$A_{ij} = \mathbb{1}[\|p_i - p_j\| \leq R] \cdot \mathbb{1}[i \neq j]$$

### 3.3 The Observation Space

Each sensor $i$ observes (for ALL sensors, not just itself):
- Remaining energy for all $N$ sensors
- Consumption energy for all $N$ sensors
- Positions $(x, y)$ for all $N$ sensors  
- Number of packets for all $N$ sensors

Total observation dimension: $5N$ (but in practice encoded as a vector $o_i \in \mathbb{R}^5$ of the agent's own local state, plus one-hot agent ID and previous action).

### 3.4 The Action Space

At each step, sensor $i$ chooses one of $N+1$ actions:
- Send packets to sensor $j$ (for $j \in \{1, \ldots, N\}$)
- Deliver directly to the BS (if within range)

An action is **valid** only if the target is within range ($\leq R$) and the sender has enough energy.

### 3.5 The Three Routing Objectives

1. **Maximize PDR** (Packet Delivery Ratio): deliver as many sensor readings as possible to BS
2. **Minimize total energy consumption**: reduce cumulative Tx + Rx energy
3. **Balance energy usage**: minimize std dev of remaining energy across all sensors

> ⚠️ **KEY DEFENSE POINT**: These objectives inherently conflict. Delivering more packets requires more transmissions (more energy). Balancing energy means using longer paths through underutilized sensors (more hops, more energy per packet). Our bi-level optimization resolves this tension.

---

## 4. The Energy Model

### 4.1 The Equations

The energy model comes from *(Su et al., IEEE TNSM, 2023)* and *(Guo et al., IJDSN, 2019)*:

$$E_T(M, d) = M \times a \times (E_{elec} + E_{amp} \times d^2)$$
$$E_R(M) = M \times a \times E_{elec}$$

Where:
| Symbol | Value | Meaning |
|--------|-------|---------|
| $E_{elec}$ | $50 \times 10^{-9}$ J/bit | Electronics energy (processing a bit) |
| $E_{amp}$ | $100 \times 10^{-12}$ J/(bit·m²) | Amplifier energy (signal strength) |
| $M$ | Number of packets sent | How many packets |
| $a$ | 512 bits | Packet size |
| $d$ | Distance in meters | Euclidean distance between sender and receiver |

### 4.2 Understanding the Physics

**Transmission**: To send $M$ packets over distance $d$:
- Each bit requires $E_{elec}$ to process (digital circuitry)
- Each bit also requires $E_{amp} \times d^2$ to amplify (radio signal must reach distance $d$)
- The $d^2$ comes from the **free-space path loss model** (standard first-order radio energy model, as used in *(Su et al., 2023)* and *(Guo et al., 2019)*): signal power decreases as the square of distance

**Reception**: To receive $M$ packets:
- Each bit requires $E_{elec}$ to process
- No amplification needed (already received)

**Key insight**: Transmission cost grows with $d^2$! Sending to a neighbor at 35m costs $(35)^2 = 1225$ times more amplifier energy per bit than sending to a neighbor at 1m. This is why multi-hop routing (short hops) can be more energy-efficient than single long hops.

### 4.3 Numerical Example

Sending 1 packet (512 bits) over 25m:
$$E_T = 1 \times 512 \times (50 \times 10^{-9} + 100 \times 10^{-12} \times 25^2)$$
$$= 512 \times (50 \times 10^{-9} + 62.5 \times 10^{-9})$$
$$= 512 \times 112.5 \times 10^{-9} = 57.6 \times 10^{-6} \text{ J} = 57.6 \text{ μJ}$$

Reception of 1 packet:
$$E_R = 1 \times 512 \times 50 \times 10^{-9} = 25.6 \text{ μJ}$$

Total per hop: $57.6 + 25.6 = 83.2$ μJ.

With $E_0 = 1$ J initial energy, a sensor can relay approximately $1 / 83.2 \times 10^{-6} \approx 12,019$ packets over 25m before dying. But in practice, sensors also transmit their own data, not just relay, so energy is shared.

---

## 5. The Reward System — Monotonic Q·K Attention Network

### 5.1 Why Not Just Sum the Rewards?

Traditional approach: $r = w_1 \cdot r_1 + w_2 \cdot r_2 + w_3 \cdot r_3 + w_4 \cdot r_4$ with fixed weights.

**Problems**:
1. The weights must be tuned by hand for each scenario
2. A linear combination can't capture complex interactions (e.g., energy efficiency matters more when batteries are low)
3. Different topologies may need different weightings

**Our approach**: Learn the weights through attention, and guarantee monotonicity so that improving any component always improves the total reward.

### 5.2 The Four Reward Components

When sensor $i$ relays packets to sensor $j$, we compute:

#### Component 1: Directional Progress ($r_1$)

$$r_1 = 1 - \frac{|\theta_{ij}|}{\pi}$$

where $\theta_{ij}$ is the angle between:
- The vector from $i$ to $j$ (the relay direction)
- The vector from $i$ to the BS (the ideal direction)

**Intuition**: If you relay toward the BS, $\theta = 0°$, so $r_1 = 1$. If you relay away from the BS, $\theta = 180°$, so $r_1 = 0$. This guides packets toward their destination.

#### Component 2: Energy Efficiency ($r_2$)

$$r_2 = 1 - \frac{E_{tx}(p_i, d_{ij}) + E_{rx}(p_i)}{E_{tx}^{max} + E_{rx}^{max}}$$

where:
- $E_{tx}^{max} = E_T(N \cdot p_0, R)$ = worst-case transmission (all sensors' packets over max range)
- $E_{rx}^{max} = E_R(N \cdot p_0)$ = worst-case reception

**Intuition**: Low energy consumption → $r_2$ close to 1. High energy consumption → $r_2$ close to 0. Normalized by worst case so it's always in $[0, 1]$.

#### Component 3: Energy Balance ($r_3$)

$$r_3 = 1 - \frac{\sigma(\mathbf{e}_{rem})}{E_0 / 2}$$

where $\sigma(\mathbf{e}_{rem})$ is the standard deviation of remaining energies across ALL sensors, and $E_0/2$ is the theoretical maximum std dev (half sensors full, half empty).

**Intuition**: If all sensors have similar energy → $\sigma \approx 0$ → $r_3 \approx 1$. If some are drained while others are full → $r_3$ is low.

**Why $E_0/2$?** By **Popoviciu's inequality** *(Popoviciu, Mathematica, 1935)*: for any bounded random variable on $[a, b]$, the maximum std dev is $(b - a)/2$. Here, remaining energies are bounded in $[0, E_0]$, so the max std dev is $E_0/2$. Concretely: if $N$ sensors — half have energy $E_0$, half have energy $0$ — mean = $E_0/2$, std dev = $\sqrt{\frac{N \cdot (E_0/2)^2}{N}} = E_0/2$.

#### Component 4: Load Balancing ($r_4$)

$$r_4 = 1 - \frac{p_j}{N \cdot p_0}$$

where $p_j$ is the packet count at receiver $j$, and $N \cdot p_0$ is the maximum possible packets (all sensors' packets at one node).

**Intuition**: Don't overload one relay node. If $j$ already has many packets, $r_4$ is low, discouraging sending more to it.

### 5.3 The Attention Mechanism — Stage 1

We have a learnable query vector $\mathbf{q} \in \mathbb{R}^{16}$ and four key vectors $\mathbf{k}_1, \mathbf{k}_2, \mathbf{k}_3, \mathbf{k}_4 \in \mathbb{R}^{16}$ (one per reward component).

The attention weights are:
$$\alpha_i = \frac{\exp(\mathbf{k}_i^\top \mathbf{q} / \sqrt{16})}{\sum_{j=1}^{4} \exp(\mathbf{k}_j^\top \mathbf{q} / \sqrt{16})}$$

Then: $\mathbf{r}' = \boldsymbol{\alpha} \odot \mathbf{r}$ (element-wise multiplication)

**Critical property**: The weights $\alpha_i$ depend ONLY on the learnable parameters $(\mathbf{q}, \mathbf{K})$, NOT on the input $\mathbf{r}$. This is unlike standard attention where keys depend on the input.

**Why this matters**: Since $\alpha_i > 0$ always (softmax outputs are always positive), if $\mathbf{r}^{(1)} \leq \mathbf{r}^{(2)}$ component-wise, then $\boldsymbol{\alpha} \odot \mathbf{r}^{(1)} \leq \boldsymbol{\alpha} \odot \mathbf{r}^{(2)}$. The partial ordering is preserved.

**Why $\sqrt{16}$?** This is the scaled dot-product attention from the Transformer paper *(Vaswani et al., "Attention Is All You Need", NeurIPS 2017, arXiv:1706.03762)*. Dividing by $\sqrt{d}$ prevents the dot products from growing too large, which would make the softmax saturate (all weight on one component).

### 5.4 The Monotonic Network — Stage 2

The weighted input $\mathbf{r}'$ passes through a **monotonic neural network** *(Sill, NeurIPS 1997)* with architecture $4 \to 16 \to 16 \to 1$:

$$g(\mathbf{r}') = \mathbf{W}_3 \cdot \text{softplus}(\mathbf{W}_2 \cdot \text{softplus}(\mathbf{W}_1 \cdot \mathbf{r}' + \mathbf{b}_1) + \mathbf{b}_2) + b_3$$

**Two key constraints**:
1. **Activation**: softplus: $\sigma(x) = \log(1 + e^x)$, NOT ReLU
2. **Weights**: $\mathbf{W}_\ell = \text{softplus}(\mathbf{W}_\ell^{raw}) \geq 0$

**Why softplus activation?** Its derivative is $\sigma'(x) = \frac{1}{1 + e^{-x}} \in (0, 1)$ — strictly positive everywhere. ReLU's derivative is 0 for negative inputs, which would break the monotonicity guarantee.

**Why non-negative weights?** Combined with strictly positive activation derivatives, the chain rule gives:
$$\frac{\partial f}{\partial r_i} = \underbrace{W_3^{(i)}}_{\geq 0} \cdot \underbrace{\sigma'(\cdot)}_{> 0} \cdot \underbrace{W_2^{(j)}}_{\geq 0} \cdot \underbrace{\sigma'(\cdot)}_{> 0} \cdot \underbrace{W_1^{(k)}}_{\geq 0} \cdot \underbrace{\alpha_i}_{> 0} \geq 0$$

### 5.5 The Monotonicity Theorem (KNOW THIS PROOF)

**Theorem**: For any $\mathbf{r}^{(1)}, \mathbf{r}^{(2)} \in [0,1]^4$ with $\mathbf{r}^{(1)} \leq \mathbf{r}^{(2)}$ component-wise: $f_\phi(\mathbf{r}^{(1)}) \leq f_\phi(\mathbf{r}^{(2)})$.

**Proof**:
1. Since $\alpha_i > 0$ for all $i$ (softmax is always positive), and $\mathbf{r}^{(1)} \leq \mathbf{r}^{(2)}$, we get $\boldsymbol{\alpha} \odot \mathbf{r}^{(1)} \leq \boldsymbol{\alpha} \odot \mathbf{r}^{(2)}$ ✓
2. For the monotonic network: at each layer, the Jacobian $\frac{\partial g}{\partial r'_i} = \sigma'(\cdot) \cdot W_i \geq 0$ because softplus derivative is strictly positive and weights are non-negative ✓
3. By the chain rule over all layers, the full composition is monotonically non-decreasing ✓

**Why does this matter?** It guarantees that a **Pareto-dominating action** (one that improves EVERY objective) always gets a higher scalar reward. Without monotonicity, pathological reward shaping could penalize Pareto improvements.

### 5.6 Reward Centering

$$\hat{f}_\phi(\mathbf{r}) = f_\phi(\mathbf{r}) - f_\phi(\mathbf{0})$$

**Why?** The network output at $\mathbf{r} = \mathbf{0}$ is a baseline offset (due to biases). Subtracting it makes the reward proportional to actual performance improvement over doing nothing. This improves the signal-to-noise ratio. $f_\phi(\mathbf{0})$ is recomputed once per episode after ES perturbation.

### 5.7 The Composite Step Reward

The final reward depends on what happened:

| Action | Reward |
|--------|--------|
| **Delivery to BS** | $r_i = 100 \times p_i$ (delivery bonus, bypasses attention network) |
| **Relay to neighbor $j$** | $r_i = \hat{f}_\phi(\mathbf{r}_i) \times 0.01 + \frac{d(i,BS) - d(j,BS)}{R} \times 0.5$ |
| **Self-loop** | $r_i = -0.1$ |
| **Out of range** | $r_i = -0.1$ |
| **Insufficient energy** | $r_i = -0.5$ |
| **Inactive** | $r_i = 0$ |

**Why $\beta_{del} = 100$?** This makes delivery overwhelmingly rewarding. Without it, agents might exploit relay rewards without ever actually delivering packets. The delivery bonus bypasses the attention network because delivery is the terminal objective — no need to balance anything.

**Why $\lambda_{attn} = 0.01$?** To prevent "relay-loop farming" — agents going back and forth between neighbors to collect small relay rewards without progressing toward the BS. The scaling ensures relay rewards are small relative to delivery.

**Progress shaping**: $\frac{d(i,BS) - d(j,BS)}{R} \times 0.5$ rewards relays that move packets closer to the BS. If $d(j,BS) < d(i,BS)$, the packet got closer → positive reward.

### 5.8 Evolution Strategies for Reward Shaping

The attention network parameters $\phi = (\mathbf{q}, \mathbf{K}, \{\mathbf{W}_\ell^{raw}, \mathbf{b}_\ell\})$ are NOT trained by backpropagation. They are trained by ES *(Salimans et al., 2017)* at the **episode level**:

**Meta-objective** (computed at episode end):
$$J = \underbrace{\left(1 - \frac{\sum_{i=1}^{N}(E_0 - e_i^{rem})}{N \cdot E_0}\right)}_{\text{energy efficiency} \in [0,1]} + \underbrace{\left(1 - \frac{\sigma(\mathbf{e}_{rem})}{E_0/2}\right)}_{\text{energy balance} \in [0,1]}$$

So $J \in [0, 2]$. Perfect score = 2 (no energy wasted, perfectly balanced).

**ES Update per episode**:
1. Sample noise: $\varepsilon \sim \mathcal{N}(0, I)$
2. Perturb: $\phi' = \phi + 0.01 \cdot \varepsilon$
3. Run episode with $\phi'$, compute $J(\phi')$
4. Advantage: $A = J(\phi') - \bar{J}$ where $\bar{J}$ is EMA baseline (decay 0.9)
5. Update: $\phi \leftarrow \phi + 0.01 \cdot A \cdot \varepsilon$ (skip if $|A| < 0.01$)

**Initialization bias**: $\mathbf{k}_2$ (energy) and $\mathbf{k}_3$ (balance) are initialized close to $\mathbf{q}$, giving them higher initial attention. This encodes the domain knowledge that energy-related objectives matter most in WSN routing.

> ⚠️ **KEY DEFENSE POINT**: The bi-level structure is crucial. The RL agents (inner loop) optimize cumulative reward, which includes a huge delivery bonus. The ES outer loop shapes the reward to also care about energy. PDR is already incentivized by the $+100$ bonus; ES handles the energy/balance tradeoff.

---

## 6. GAPF Architecture — Every Layer, Every Parameter

### 6.1 The Idea

GAPF sits **on top** of the pre-trained, frozen QMIX and QTRAN experts. At the start of each episode, GAPF:
1. Looks at the sensor topology (who is where, who can communicate with whom)
2. Encodes this topology into a 16-dimensional vector
3. Decides: use QMIX or QTRAN for this episode?

### 6.2 Step-by-Step Architecture

#### Step 1: Graph Construction

Given $N$ sensor positions and radius $R$:

1. **Binary adjacency matrix**: $A_{ij} = \mathbb{1}[\|p_i - p_j\| \leq R] \cdot \mathbb{1}[i \neq j]$
2. **Self-loops**: $\tilde{\mathbf{A}} = \mathbf{A} + \mathbf{I}_N$
3. **Degree matrix**: $\tilde{D}_{ii} = \sum_j \tilde{A}_{ij}$
4. **Symmetric normalization**: $\hat{\mathbf{A}} = \tilde{\mathbf{D}}^{-1/2} \tilde{\mathbf{A}} \tilde{\mathbf{D}}^{-1/2}$

**Why self-loops?** Without $\mathbf{I}_N$, a node only aggregates neighbors' features. With self-loops, it also keeps its own features. This prevents information loss.

**Why symmetric normalization?** Consider two nodes: one with degree 2, one with degree 50. After aggregation, the high-degree node would have 50x larger feature values. Normalization prevents this scale imbalance. The $D^{-1/2}$ on BOTH sides (not just one) is the specific recipe from *(Kipf & Welling, ICLR 2017)* — it averages contributions from both the sending and receiving side, giving a "geometric mean" normalization.

#### Step 2: Node Features

Each sensor $i$ gets a 4-dimensional feature vector:
$$\mathbf{x}_i = \left[\frac{x_i}{L}, \frac{y_i}{L}, \frac{\|p_i - p_{BS}\|}{\max_j \|p_j - p_{BS}\|}, \frac{\deg(i)}{\max_j \deg(j)}\right]$$

| Feature | Meaning | Why it matters |
|---------|---------|----------------|
| $x_i / L$ | Normalized x-position | Where is the sensor? |
| $y_i / L$ | Normalized y-position | Where is the sensor? |
| Distance to BS (normalized) | How far from BS? | Closer sensors can deliver directly |
| Degree (normalized) | How many neighbors? | High-degree nodes are relay hubs |

All features are in $[0, 1]$. $L$ is the field size (100m in our setup).

#### Step 3: GCN Encoder (Two Layers) *(Kipf & Welling, 2017)*

**Layer 1**: $\mathbf{H}^{(1)} = \text{ReLU}(\hat{\mathbf{A}} \mathbf{X} \mathbf{W}_1)$ where $\mathbf{W}_1 \in \mathbb{R}^{4 \times 16}$

What happens: Each node's features are combined with its neighbors' features (via $\hat{\mathbf{A}}$), then projected from 4D to 16D, then passed through ReLU.

**Layer 2**: $\mathbf{Z} = \hat{\mathbf{A}} \mathbf{H}^{(1)} \mathbf{W}_2$ where $\mathbf{W}_2 \in \mathbb{R}^{16 \times 16}$

What happens: Another round of neighbor aggregation and linear projection. No activation here (the output is the raw embedding).

**After two layers**, each node's representation incorporates information from its **2-hop neighborhood** (neighbors of neighbors). This captures the local structure.

#### Step 4: Mean-Pool Readout

$$\mathbf{z} = \frac{1}{N} \sum_{i=1}^{N} \mathbf{Z}_{i,:} \in \mathbb{R}^{16}$$

This averages all node embeddings into one graph-level embedding.

**Why mean-pool?** 
1. It's **permutation-invariant**: the order of sensors doesn't matter
2. It handles **variable-size** graphs: whether you have 20 or 100 sensors, the output is always $\mathbb{R}^{16}$
3. It captures the "average structure" of the graph

#### Step 5: CAS Controller (MLP)

$$p_{QMIX} = \sigma\left(\mathbf{w}_2^\top \text{ReLU}(\mathbf{W}_c \mathbf{z} + \mathbf{b}_c) + b_2\right)$$

Where:
- $\mathbf{W}_c \in \mathbb{R}^{64 \times 16}$: projects 16D embedding to 64D
- $\mathbf{b}_c \in \mathbb{R}^{64}$: bias
- $\mathbf{w}_2 \in \mathbb{R}^{64}$: projects 64D to scalar
- $b_2 \in \mathbb{R}$: bias
- $\sigma$: sigmoid function (maps to $[0, 1]$)

**During training**: $a^{meta} \sim \text{Bernoulli}(p_{QMIX})$ — randomly sample (exploration)
**During evaluation**: $a^{meta} = \text{QMIX}$ if $p_{QMIX} > 0.5$, QTRAN otherwise (greedy)

### 6.3 Parameter Count — The 1,473 Number

$$|\theta| = \underbrace{4 \times 16 + 16 \times 16}_{GCN: 320} + \underbrace{16 \times 64 + 64 + 64 \times 1 + 1}_{CAS: 1,153} = 1,473$$

Let's verify:
- $\mathbf{W}_1$: $4 \times 16 = 64$ parameters
- $\mathbf{W}_2$: $16 \times 16 = 256$ parameters
- GCN total: $64 + 256 = 320$ ✓
- $\mathbf{W}_c$: $64 \times 16 = 1,024$ parameters
- $\mathbf{b}_c$: $64$ parameters
- $\mathbf{w}_2$: $64$ parameters
- $b_2$: $1$ parameter
- CAS total: $1,024 + 64 + 64 + 1 = 1,153$ ✓
- **Grand total: $320 + 1,153 = 1,473$** ✓

For comparison, a single RNN agent has 38,983 parameters. GAPF is **26× smaller**.

> ⚠️ **DEFENSE NOTE**: No GCN biases are included in GAPF. If they ask, confirm that the GCN layers as formulated don't have bias terms — only $\hat{\mathbf{A}} \mathbf{X} \mathbf{W}$.

---

## 7. Training Procedure

### 7.1 Three-Phase Training

**Phase 1: Train QMIX** (independently)
- 200,000 timesteps (~2,000 episodes of 100 steps)
- Adam optimizer, lr = 0.0003
- ε-greedy exploration: 0.5 → 0.01 over 150,000 steps
- Replay buffer: 15,000 episodes, batch size 32
- Target network: hard update every 30 episodes
- Discount factor γ = 0.99

**Phase 2: Train QTRAN** (independently, same hyperparameters except)
- RMSprop optimizer (instead of Adam)
- Additional loss terms: optimality weight λ_opt = 1.0, non-optimality weight λ_nopt = 0.1

**Phase 3: Train GAPF meta-controller** (experts are FROZEN)
- 2,000 episodes
- Adam optimizer, lr = 0.003 (10× higher than experts — small model converges fast)
- Gradient clipping: norm ≤ 1.0
- EMA baseline: β = 0.95
- On-policy: batch size 1 (each episode = one update)
- REINFORCE policy gradient *(Williams, 1992)*

### 7.2 GAPF Training Algorithm (Step by Step)

```
Initialize θ randomly (Xavier uniform)
Initialize Adam optimizer
b = None (EMA baseline)

For episode k = 1 to 2,000:
    1. Reset environment, get sensor positions
    2. Build adjacency matrix and normalize: Â
    3. Extract node features: X
    4. GCN forward pass → graph embedding z ∈ ℝ¹⁶
    5. CAS forward pass → p_QMIX ∈ (0, 1)
    6. Sample: a_meta ~ Bernoulli(p_QMIX)
    7. Run full episode with selected expert → return G_k
    8. If b is None: b = G_k
    9. Advantage: δ = G_k - b
    10. Update baseline: b = 0.95 × b + 0.05 × G_k
    11. If |δ| > 10⁻⁸:
        Loss = -δ × log μ_θ(a_meta | G_k)
        θ ← θ - lr × Adam(clip(∇Loss, 1.0))
```

### 7.3 Why REINFORCE Instead of DQN?

The meta-controller makes a **binary decision** (QMIX or QTRAN) once per episode. This is a bandit problem with a single action per "trial." REINFORCE is the natural choice because:
- The action space is binary (Bernoulli)
- We get one reward per episode (not per step)
- No need for a replay buffer or target network for such a simple decision
- The EMA baseline reduces variance sufficiently

---

## 8. Time Complexity

### 8.1 Per-Step Inference (During Execution)

Each agent $i$ runs: input projection → GRU → Q-value output → argmax

$$\mathcal{O}_{step} = \mathcal{O}(n^2 h + n h^2)$$

Where $n$ = number of sensors, $h$ = 64 (GRU hidden dim).

- The $n^2 h$ comes from: each agent produces Q-values for $n+1$ actions (one per neighbor), and there are $n$ agents
- The $n h^2$ comes from: each GRU has $3 \times h^2$ gate computations, across $n$ agents

**This is IDENTICAL for QMIX, QTRAN, and GAPF** at execution time. The mixer is training-only.

### 8.2 Episode-Level GAPF Overhead

$$\mathcal{O}_{GAPF-init} = \mathcal{O}(n^2 d) \text{ where } d = 16$$

This includes adjacency construction ($n^2$), GCN forward pass ($n^2 d + n d^2$), and CAS MLP ($dm$).

### 8.3 Total Episode Complexity

$$\mathcal{O}_{GAPF} = \underbrace{T \cdot \mathcal{O}(n^2 h)}_{\text{T=100 steps}} + \underbrace{\mathcal{O}(n^2 d)}_{\text{one-time GCN}}$$

Since $T \cdot h \gg d$ (100 × 64 = 6,400 ≫ 16), the GCN overhead is **negligible**.

### 8.4 Comparison with QPSOFL

QPSOFL *(Hu et al., Scientific Reports, 2024)* (the metaheuristic baseline) has per-episode cost: $\mathcal{O}(T \cdot I \cdot N_p \cdot n^2)$ where $I = 50$ (PSO iterations) and $N_p = 32$ (particles). This is $50 \times 32 = 1,600\times$ more than a single step of GAPF, explaining why QPSOFL has longer wall-clock times.

---

## 9. Results — Know Every Number

### 9.1 Experimental Setup

| Parameter | Value |
|-----------|-------|
| Field size | 100m × 100m |
| BS position | (50, 50) — center |
| Initial energy $E_0$ | 1 J |
| Packet size | 512 bits |
| Initial packets per sensor | 1 |
| Episode length | 100 steps |
| Total training timesteps | 200,000 |
| Test episodes | 1,000 per scenario per seed |
| Seeds | 42, 123, 456 (3 seeds × 7 scenarios × 1,000 episodes = **21,000 test episodes**) |

### 9.2 The Seven Scenarios

| # | Sensors ($n$) | Radius ($R$) | Rationale |
|---|----------|----------|-----------|
| 1 | 20 | 25m | Sparse, extreme connectivity challenge |
| 2 | 30 | 25m | Small-medium, limited relay options |
| 3 | 50 | 35m | Medium, moderate density |
| 4 | 70 | 35m | Baseline — dense, standard range |
| 5 | 70 | 45m | Dense with extended range |
| 6 | 100 | 35m | Large-scale scalability test |
| 7 | 100 | 50m | Large-scale, high connectivity |

### 9.3 Key Numbers (MEMORIZE THESE)

| Scenario | GAPF PDR | QMIX PDR | Improvement | GAPF σ_E | QMIX σ_E | Balance ratio |
|----------|----------|----------|-------------|----------|----------|---------------|
| n=20, R=25 | **75.3%** | 55.9% | **+35%** | 0.0043 | 0.0075 | 1.7× |
| n=30, R=25 | **87.7%** | 56.8% | **+54%** | 0.0035 | 0.0111 | 3× |
| n=50, R=35 | **99.0%** | 55.3% | **+79%** | 0.0039 | 0.0264 | 7× |
| n=70, R=35 | **98.0%** | 54.5% | **+80%** | 0.0049 | 0.0318 | 6.5× |
| n=70, R=45 | **98.0%** | 66.7% | **+47%** | 0.0061 | 0.0379 | 6× |
| n=100, R=35 | **98.0%** | 46.4% | **+111%** | 0.0061 | 0.0455 | 7.5× |
| n=100, R=50 | **98.0%** | 66.9% | **+43%** | 0.0061 | 0.0559 | 9× |

### 9.4 Five Principal Findings

**F1: GAPF's PDR advantage grows with sparsity**
- Sparse (R=35): +35% → +54% → +79% → +80% → +111%
- Dense (R=45/50): +47% → +43%
- **Interpretation**: In sparse networks, GAPF's topology awareness helps find viable relay paths that QMIX/QTRAN miss.

**F2: 2-3.5× less energy, 3-9× better balance**
- GAPF delivers MORE data while using LESS energy
- This is "energy-coherent routing": QMIX/QTRAN waste energy on failed transmissions

**F3: QMIX ≈ QTRAN**
- Their PDR differs by only 1-2% across all scenarios
- This proves GAPF's gain comes from topology-aware policy fusion, not from one expert being better

**F4: QPSOFL *(Hu et al., 2024)* collapses at scale**
- PDR: 7.5% (n=20) → <10% (n=100, R=35)
- Its low energy consumption is meaningless — it barely delivers any packets
- Exception: at high R (n=100, R=50), QPSOFL reaches 44.8% PDR

**F5: GAPF is the only algorithm passing ALL feasibility constraints**
- QMIX/QTRAN FAIL memory (3.2 GB → 13.8 GB vs 1 GB limit)
- GAPF: 684-951 MB (within 1 GB)
- All pass latency (p99 < 50 ms)

### 9.5 Inference Metrics (N=70)

| Algorithm | Latency p95 | Peak RAM | MACs | Energy |
|-----------|-------------|----------|------|--------|
| QMIX (agent+mixer) | 0.27 ms | 2.98 KB | 2,539,904 | 27.2 μJ |
| QTRAN (agent+mixer) | 0.17 ms | 34.32 KB | 4,955,532 | 16.7 μJ |
| GAPF (GCN, gateway) | 0.03 ms | 4.12 KB | 181,408 | 3.0 μJ |
| Agent only (deployed) | <1 ms | ~2 KB | ~29K | <10 μJ |

Even scaling by 50× for ARM Cortex-M4 at 80 MHz *(hardware benchmarks per David et al., MLSys 2021; Banbury et al., NeurIPS 2021)*: $1 \text{ ms} \times 50 = 50 \text{ ms}$ — still real-time.

---

## 10. Deployment Feasibility

The CTDE paradigm *(Kraemer & Banerjee, 2016; Lowe et al., 2017)* decouples training from deployment.

### 10.1 What Runs Where

| Component | Where | Deployed? | Size |
|-----------|-------|-----------|------|
| QMIX/QTRAN mixer | Training server | **No** | — |
| Monotonic Attention | Training server | **No** | — |
| ES loop | Training server | **No** | — |
| GAPF meta-controller | Sink/gateway | Yes (once/episode) | ~6 KB |
| Per-sensor GRU agent | Each sensor | Yes (once/step) | ~100 KB |

### 10.2 Per-Sensor Agent Details

Architecture on each sensor:
$$a_i = \arg\max_j \mathbf{W}_2 \cdot \text{GRU}(\text{ReLU}(\mathbf{W}_1 \mathbf{o}_i + \mathbf{b}_1), \mathbf{h}_i^{(t-1)}) + \mathbf{b}_2$$

- Input: $\mathbf{o}_i \in \mathbb{R}^5$ (remaining energy, consumed energy, x, y, packet count)
- Hidden state: $\mathbf{h}_i \in \mathbb{R}^{64}$
- Output: Q-values $\in \mathbb{R}^{N+1}$

**~29,000 MACs per step** = 
- Input layer: 320 MACs
- GRU cell: 24,576 MACs (3 gates × 2 × 64²)
- Output layer: 4,544 MACs (at n=70)

### 10.3 Target Hardware

| Resource | Agent needs | STM32L4 has | nRF52840 has |
|----------|-------------|-------------|--------------|
| Flash | ~100 KB | 1 MB | 1 MB |
| SRAM | ~2 KB | 256 KB | 256 KB |
| Compute | ~29K MACs | 80 MHz M4 | 64 MHz M4 |

**Deployment**: Extract weights as C arrays → implement GRU in ~100 lines of C → flash to MCU → done. Toolchains such as TensorFlow Lite Micro *(David et al., MLSys 2021)* and TVM *(Chen et al., OSDI 2018)* support this workflow. Hardware benchmarks from MLPerf Tiny *(Banbury et al., NeurIPS 2021)* confirm Cortex-M4 handles these workloads.

---

## 11. Limitations — Be Honest Before They Ask

1. **Simulation-only**: No hardware-in-the-loop experiments. No channel fading, packet collisions, clock drift.

2. **Static topology per episode**: GCN runs once per episode. If sensors move mid-episode, the embedding is stale. (Step-level Fusion mode exists but wasn't the main focus.)

3. **Two experts only**: Binary selection (QMIX vs QTRAN). Extending to k > 2 experts requires softmax over k outputs.

4. **Fixed episode length (T=100)**: Real WSNs run continuously. The episodic formulation doesn't capture long-horizon energy depletion.

5. **Memory at n=100**: 951 MB — only 7% headroom below the 1 GB constraint. Scaling to n > 100 needs compression.

6. **Homogeneous sensors**: All sensors identical. No mixed hardware, asymmetric energy budgets, or varied transmission power.

---

## 12. Likely Brutal Questions and How to Answer Them

### Q1: "Why not just use QMIX? Why do you need GAPF?"

**Answer**: QMIX alone achieves only 46-67% PDR across our scenarios. GAPF achieves ≥98%. The key is topology awareness — GAPF's GCN sees the graph structure and selects the expert that works best for that specific deployment. Different random topologies favor different experts. The gain is +43% to +111% PDR with 2-3.5× less energy.

### Q2: "But your results show QMIX ≈ QTRAN. So how can selecting between them help?"

**Answer**: Excellent observation. QMIX and QTRAN have similar *average* performance, but they perform differently on *specific topologies*. Our results show the CAS controller selects QMIX 100% for some seeds and QTRAN 100% for others — it adapts to the topology realization, not the algorithm identity. The GCN embedding captures structural properties (connectivity, clustering, BS proximity) that correlate with expert performance per-topology.

### Q3: "Explain the monotonicity proof."

**Answer**: 
1. Softmax always outputs positive values, so attention weights α_i > 0
2. If reward vector r¹ ≤ r² component-wise, then α ⊙ r¹ ≤ α ⊙ r² (positive scaling preserves order)
3. In the monotonic network, all weights are non-negative (enforced via softplus on raw weights), and softplus activation has strictly positive derivative
4. Chain rule: derivative of output w.r.t. each input = product of non-negative terms = non-negative
5. Therefore, the whole function is monotonically non-decreasing

### Q4: "Why Evolution Strategies instead of backpropagation for the reward network?"

**Answer**: The reward network parameters affect the RL training process, which runs for an entire episode (100 steps). To backpropagate through this, you'd need to differentiate through the entire episode — all 100 steps, all N agents, all GRU hidden states. This is computationally prohibitive and numerically unstable (vanishing/exploding gradients through 100 steps). ES is gradient-free: perturb, evaluate, update. It only needs the final episode-level metric J, not per-step gradients.

### Q5: "What is the meta-objective J, and why those specific components?"

**Answer**: J = (energy efficiency) + (energy balance), both in [0,1], so J ∈ [0,2]. We don't include PDR in J because PDR is already strongly incentivized by the +100 delivery bonus in the step reward. If we added PDR to J, the ES would try to shape rewards for delivery, which competes with the already-dominant delivery bonus and destabilizes training. The ES outer loop only needs to handle what the inner loop doesn't naturally optimize: energy usage.

### Q6: "Why 1,473 parameters? Why not more?"

**Answer**: Fewer parameters is a feature, not a bug. (1) With frozen experts and REINFORCE (high variance), a small model converges faster and more reliably. (2) 1,473 parameters cannot memorize training topologies, forcing genuine structural learning. (3) The GCN output is 16D — there isn't enough information capacity to justify a larger controller. (4) Deployment: 6 KB is negligible on a gateway device.

### Q7: "How do you guarantee the energy model is realistic?"

**Answer**: Our energy model (first-order radio model) is the standard in WSN literature, directly adopted from *(Su et al., IEEE TNSM, 2023)* and *(Guo et al., IJDSN, 2019)*, and widely used in cluster-based routing works such as *(Biabani et al., 2020)*, *(Yao et al., 2022)*, and *(Kodati et al., 2024)*. The $d²$ term captures free-space path loss. $E_{elec} = 50$ nJ/bit and $E_{amp} = 100$ pJ/(bit·m²) values are well-established benchmarks from these references. However, this model simplifies real-world effects like multipath fading, interference, and protocol overhead. This is acknowledged as a limitation.

### Q8: "Why GCN and not GAT (Graph Attention Network)?"

**Answer**: Graph Attention Networks (GATs) add learnable attention weights over neighbors, making them more expressive but also more expensive ($\mathcal{O}(n^2 d)$ per layer with attention weights). We deliberately chose the simpler GCN formulation from *(Kipf & Welling, ICLR 2017)* because our GCN runs only once per episode and the goal is a graph-level summary (not fine-grained node decisions). The mean-pool readout averages over all nodes anyway, reducing the benefit of per-node attention. The simplicity also keeps the parameter count minimal (320 GCN params).

### Q9: "QPSOFL uses less energy in most scenarios. Isn't that better?"

**Answer**: QPSOFL *(Hu et al., 2024)* has low energy consumption, but this is an artifact of not delivering packets. At n=100, R=35: QPSOFL delivers only 9.9% of packets. Of course it uses little energy — it barely transmits! Among algorithms with viable PDR (>50%), GAPF consistently uses the least energy. QPSOFL demonstrates that energy conservation without delivery is meaningless.

### Q10: "What happens if both experts are bad for a topology?"

**Answer**: GAPF can only be as good as its best expert. If both QMIX and QTRAN fail on a particular topology, GAPF fails too. This is a fundamental limitation of the CAS (selection) approach. The alternative — Fusion mode (blending Q-values at every step) — partially addresses this but was not the main focus of this paper. Future work: add more diverse experts (MAPPO, DQN, QPLEX).

### Q11: "Why 7 scenarios? How did you choose them?"

**Answer**: We systematically vary two independent variables: network size (n ∈ {20, 30, 50, 70, 100}) and coverage radius (R ∈ {25, 35, 45, 50}). This creates a matrix from sparse-small to dense-large. Each scenario is run with 3 random seeds (42, 123, 456) × 1,000 test episodes = 3,000 episodes per scenario, 21,000 total. The seeds ensure we don't report lucky initializations.

### Q12: "What is the GRU and why use it instead of LSTM?"

**Answer**: GRU (Gated Recurrent Unit) has two gates: reset gate and update gate. LSTM has three: forget, input, output. GRU is the standard RNN agent architecture in the EPyMARL framework used in our work (inherited from the QMIX/QTRAN implementations). GRU has fewer parameters (~38K vs ~50K for LSTM at hidden=64) and performs comparably on short sequences. Since our episodes are only 100 steps, the extra expressiveness of LSTM is unnecessary, and the smaller GRU fits better on resource-constrained sensors.

### Q13: "Explain the symmetric normalization equation."

**Answer**: 
1. Start with adjacency A (who connects to whom)
2. Add self-loops: $\tilde{A} = A + I$ (each node connects to itself)
3. Compute degree: $\tilde{D}_{ii}$ = sum of row i of $\tilde{A}$ (how many connections including self)
4. $\tilde{D}^{-1/2}$: take the square root of each diagonal entry, then invert
5. $\hat{A} = \tilde{D}^{-1/2} \tilde{A} \tilde{D}^{-1/2}$: multiply on both sides

**Effect** *(Kipf & Welling, ICLR 2017)*: The $(i,j)$ entry of $\hat{A}$ is $\frac{1}{\sqrt{\tilde{d}_i \cdot \tilde{d}_j}}$ if $i$ and $j$ are connected (or $i=j$). This means a message from a high-degree node to a low-degree node is down-weighted, and vice versa. It normalizes the spectral properties of the graph Laplacian, which is important for stable training.

### Q14: "Why is the delivery bonus 100 and not 10 or 1000?"

**Answer**: The value 100 was empirically chosen to be large enough that delivery dominates all relay rewards (which are scaled by λ_attn = 0.01, typically producing values < 1). At 100, delivering 1 packet gives reward 100, while the best possible relay reward is ~0.015. This 6,000:1 ratio ensures agents always prioritize delivery. Making it 1,000 would work too but could slow learning (large reward variance). Making it 10 might not dominate relay rewards enough.

### Q15: "What is the EMA baseline and why β = 0.95?"

**Answer**: EMA = Exponential Moving Average. It tracks the running average of episode returns: $b_{k+1} = 0.95 \cdot b_k + 0.05 \cdot G_k$. This means the baseline adapts slowly (95% weight on history, 5% on current episode). Purpose: in REINFORCE, $(G_k - b_k)$ replaces $G_k$ to reduce variance. If $G_k > b_k$, the action was better than average → reinforce it. If $G_k < b_k$, the action was worse → discourage it. β = 0.95 gives a smooth baseline that doesn't react to every fluctuation but still tracks long-term trends.

### Q16: "Your memory at n=100 is 951 MB with only 7% headroom. Isn't that dangerously close?"

**Answer**: Yes, this is a real concern. At n=100, we're at the practical limit. For n>100, model compression (8-bit quantization, pruning, or knowledge distillation into a single policy) would be necessary. We explicitly acknowledge this as a limitation. However, 100 sensors is already large for most WSN disaster monitoring deployments.

### Q17: "Why not train end-to-end with a single, more powerful algorithm?"

**Answer**: Three reasons: (1) End-to-end training at 100 sensors with MARL requires massive replay buffers (QMIX/QTRAN use 13 GB), making it infeasible on constrained gateways. (2) Frozen experts preserve independently validated performance — no catastrophic forgetting. (3) GAPF's 1,473-parameter meta-controller converges in 2,000 episodes; training a new end-to-end model from scratch would take orders of magnitude more data.

### Q18: "How is this 'near real-time'?"

**Answer**: All algorithms achieve sub-millisecond inference latency on host hardware. Even scaling by 50× for a Cortex-M4 at 80 MHz, the worst-case per-step decision time is <15 ms. Our feasibility framework automatically records p95 and p99 latencies, and all pass the 50 ms budget across every scenario. The step-level decision (which neighbor to relay to) happens in <1 ms — well within real-time WSN routing requirements.

---

## Summary Cheat Sheet

| What | Number | Why it matters |
|------|--------|----------------|
| GAPF parameters | 1,473 | 26× smaller than one expert |
| Expert parameters | 38,983 | Per agent (GRU) |
| GCN embedding dim | 16 | Compact topology representation |
| CAS hidden dim | 64 | Sufficient for binary decision |
| Delivery bonus | 100 | Dominates relay rewards |
| λ_attn | 0.01 | Prevents relay-loop farming |
| ES noise σ | 0.01 | Small perturbations for stable reward shaping |
| ES learning rate | 0.01 | Outer loop adapts slowly |
| RL learning rate | 0.0003 | Inner loop (QMIX/QTRAN) |
| GAPF learning rate | 0.003 | 10× higher (tiny model) |
| EMA baseline β | 0.95 | Smooth REINFORCE baseline |
| Episode length T | 100 steps | Fixed |
| Test episodes | 21,000 total | 7 scenarios × 3 seeds × 1,000 |
| Best PDR improvement | +111% | n=100, R=35 |
| Best energy balance | 9× better | n=100, R=50 |
| Memory savings | 13× less | 951 MB vs 13.2 GB |
| Agent on sensor | ~100 KB | Fits STM32L4, nRF52840 |
| Agent inference | ~29K MACs | <1 ms on Cortex-M4 |

---

> **Final advice**: When answering questions, always start with the INTUITION, then give the MATH, then give the NUMBER. Example: "We use softplus instead of ReLU because [intuition: we need strictly positive derivatives for monotonicity]. Mathematically, softplus'(x) = 1/(1+e^{-x}) ∈ (0,1), which is always positive, unlike ReLU'(x) which is 0 for x<0. This guarantees the Jacobian ∂f/∂r_i ≥ 0."

Good luck! You know this material deeply. 🎓

---

## References (Verified — All From the Article's Bibliography)

Every inline citation above traces to one of these published works. No placeholder or fabricated references.

| Tag | Full Reference |
|-----|----------------|
| *(EEA Glossary)* | European Environment Agency, "Disaster" (Glossary term). URL: https://www.eea.europa.eu/help/glossary/eea-glossary/disaster-1 |
| *(Statista, 2023)* | Statista, "Number of natural disasters per year worldwide 2023." URL: https://www.statista.com/statistics/510959/number-of-natural-disasters-events-globally/ |
| *(Burgueño Salas, Statista, 2023)* | Burgueño Salas, E., "Global natural disaster deaths per year 2023," Statista. URL: https://www.statista.com/statistics/510952/number-of-deaths-from-natural-disasters-globally/ |
| *(Al Qundus et al., 2020)* | Al Qundus, J., Dabbour, K., Gupta, S., Meissonier, R., & Paschke, A., "Wireless sensor network for AI-based flood disaster detection," *Annals of Operations Research*, Springer, 2020, pp. 1–23. |
| *(Yarali, 2020)* | Yarali, A., *Wireless Sensor Networks (WSN): Technology and Applications*, Nova Science Publishers, 2020. |
| *(Biabani et al., 2020)* | Biabani, M., Fotouhi, H., & Yazdani, N., "An Energy-Efficient Evolutionary Clustering Technique for Disaster Management in IoT Networks," *Sensors*, 20(9), 2647, 2020. DOI: 10.3390/s20092647 |
| *(Hosseinzadeh et al., 2022)* | Hosseinzadeh, M. et al., "A Hybrid Delay Aware Clustered Routing Approach Using Aquila Optimizer and Firefly Algorithm in Internet of Things," *Mathematics*, 10(22), 4331, 2022. DOI: 10.3390/math10224331 |
| *(Chaurasia et al., 2023)* | Chaurasia, S., Kumar, K., & Kumar, N., "MOCRAW: A Meta-heuristic Optimized Cluster head selection based Routing Algorithm for WSNs," *Ad Hoc Networks*, 141, 103079, 2023. DOI: 10.1016/j.adhoc.2022.103079 |
| *(Su et al., IEEE TNSM, 2023)* | Su, X., Ren, Y., Cai, Z., Liang, Y., & Guo, L., "A Q-Learning-Based Routing Approach for Energy Efficient Information Transmission in Wireless Sensor Network," *IEEE Trans. Network and Service Management*, 20(2), 1949–1961, 2023. DOI: 10.1109/TNSM.2022.3218017 |
| *(Guo et al., IJDSN, 2019)* | Guo, W., Yan, C., & Lu, T., "Optimizing the lifetime of wireless sensor networks via reinforcement-learning-based routing," *Int. J. Distributed Sensor Networks*, 15(2), 2019. DOI: 10.1177/1550147719833541 |
| *(Ding et al., 2022)* | Ding, R. et al., "Packet Routing in Dynamic Multi-Hop UAV Relay Network: A Multi-Agent Learning Approach," *IEEE Trans. Vehicular Technology*, 71(9), 10059–10072, 2022. DOI: 10.1109/TVT.2022.3182335 |
| *(MARL Textbook, MIT Press 2024)* | "Multi-Agent Reinforcement Learning: Foundations and Modern Approaches," MIT Press, 2024. URL: https://www.marl-book.com/ |
| *(Son et al., 2019)* | Son, K., Kim, D., Kang, W. J., Hostallero, D. E., & Yi, Y., "QTRAN: Learning to Factorize with Transformation for Cooperative Multi-Agent Reinforcement Learning," *ICML*, arXiv:1905.05408, 2019. |
| *(Kipf & Welling, ICLR 2017)* | Kipf, T. N. & Welling, M., "Semi-Supervised Classification with Graph Convolutional Networks," *ICLR*, 2017. |
| *(Williams, 1992)* | Williams, R. J., "Simple statistical gradient-following algorithms for connectionist reinforcement learning," *Machine Learning*, 8(3–4), 229–256, 1992. |
| *(Salimans et al., 2017)* | Salimans, T., Ho, J., Chen, X., Sidor, S., & Sutskever, I., "Evolution Strategies as a Scalable Alternative to Reinforcement Learning," arXiv:1703.03864, 2017. |
| *(Vaswani et al., NeurIPS 2017)* | Vaswani, A. et al., "Attention Is All You Need," *NeurIPS*, arXiv:1706.03762, 2017. |
| *(Sill, NeurIPS 1997)* | Sill, J., "Monotonic Networks," *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 10, MIT Press, 1997. |
| *(Popoviciu, 1935)* | Popoviciu, T., "Sur les équations algébriques ayant toutes leurs racines réelles," *Mathematica*, 9, 129–145, 1935. |
| *(Hu et al., Scientific Reports, 2024)* | Hu, H., Fan, X., & Wang, C., "Energy efficient clustering and routing protocol based on quantum particle swarm optimization and fuzzy logic for wireless sensor networks," *Scientific Reports*, 14, 18595, 2024. DOI: 10.1038/s41598-024-69360-0 |
| *(Kraemer & Banerjee, 2016)* | Kraemer, L. & Banerjee, B., "Multi-agent reinforcement learning as a rehearsal for decentralized planning," *Neurocomputing*, 190, 82–94, 2016. |
| *(Lowe et al., 2017)* | Lowe, R. et al., "Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments," *NeurIPS*, 2017. |
| *(David et al., MLSys 2021)* | David, R. et al., "TensorFlow Lite Micro: Embedded Machine Learning for TinyML Systems," *MLSys*, 2021. |
| *(Chen et al., OSDI 2018)* | Chen, T. et al., "TVM: An Automated End-to-End Optimizing Compiler for Deep Learning," *OSDI*, 2018. |
| *(Banbury et al., NeurIPS 2021)* | Banbury, C., Reddi, V. J., Torelli, P. et al., "MLPerf Tiny Benchmark," *NeurIPS Datasets and Benchmarks Track*, 2021. |
| *(Yao et al., 2022)* | Yao, Y.-D. et al., "Energy-Efficient Routing Protocol Based on Multi-Threshold Segmentation in Wireless Sensors Networks for Precision Agriculture," *IEEE Sensors Journal*, 22(7), 6216–6231, 2022. DOI: 10.1109/JSEN.2022.3150770 |
| *(Kodati et al., 2024)* | Kodati, S. et al., "Hybrid grasshopper and Harris hawk optimization algorithm-based energy efficient routing protocol," *Int. J. Communication Systems*, 37(13), e5851, 2024. DOI: 10.1002/dac.5851 |

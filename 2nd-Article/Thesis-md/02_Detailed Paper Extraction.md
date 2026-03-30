# Detailed Structured Extraction of Key Works for Literature Review

**Topic:** Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for 6G-Integrated Disaster Sensor Networks: A Lifecycle-Sustainable Approach

***

## Section A: Energy-Efficient and AI-Based Routing in WSNs

### A1. Priyadarshi et al. (2025) — AI-Based Routing Framework

| Field | Detail |
|-------|--------|
| **Full Citation** | R. Priyadarshi, R. R. Kumar, R. Ranjan & P. V. Kumar, "AI-based routing algorithms improve energy efficiency, latency, and data reliability in wireless sensor networks," *Scientific Reports*, vol. 15, 22292, Jul. 2025. [DOI: 10.1038/s41598-025-08677-w](https://doi.org/10.1038/s41598-025-08677-w) |
| **Objective** | Propose a modular AI-based routing framework for WSNs integrating reinforcement learning (RL), supervised learning, and swarm intelligence (GA, PSO) into a structured decision-making pipeline[^1]. |
| **Methodology** | Each AI module plays a distinct role: RL handles local routing decisions, while GA and PSO are invoked for global optimization under resource constraints. Simulations conducted in MATLAB R2021b validate effectiveness[^2]. |
| **Key Results** | Demonstrated improvements in packet delivery ratio (PDR), end-to-end latency, and energy efficiency compared to traditional protocols. The hybrid AI framework outperformed standalone algorithms in dynamic network conditions[^1]. |
| **Limitations** | Based on synthetic simulations only; real-world deployment challenges (scalability, resource usage, security) are acknowledged but not resolved. No sustainability or carbon metrics considered[^2]. |
| **Thematic Relevance** | AI-based routing, energy efficiency, adaptive routing — foundational for carbon-aware routing extensions. |

***

### A2. Soltani et al. (2025) — Multi-Agent Reinforcement Learning Routing

| Field | Detail |
|-------|--------|
| **Full Citation** | P. Soltani, M. Eskandarpour, A. Ahmadizad & H. Soleimani, "Energy-Efficient Routing Algorithm for Wireless Sensor Networks: A Multi-Agent Reinforcement Learning Approach," *arXiv:2508.14679*, Aug. 2025. [Link](https://arxiv.org/abs/2508.14679) |
| **Objective** | Develop adaptive multi-hop routing using multi-agent RL (Q-learning) for dynamic, energy-aware path selection in WSNs[^3]. |
| **Methodology** | Each sensor node modeled as an autonomous agent observing residual energy, distance to sink, hop count, and hotspot proximity. Reward function incentivizes balanced load distribution and hotspot avoidance. RL-driven decisions fused with classical MERA and MST algorithms[^4]. |
| **Key Results** | Significantly improved node survival rate, reduced SoC variance, and enhanced network resilience compared to classical graph-based methods[^3]. |
| **Limitations** | RL training convergence time may be impractical in rapidly evolving disaster scenarios. Cloud-based training offloading assumes connectivity that may not exist post-disaster[^3]. |
| **Thematic Relevance** | Autonomous routing, energy efficiency, adaptive multi-hop — directly relevant to self-healing routing in disaster contexts. |

***

### A3. Zhang & Liu (2025) — RL + Metaheuristic Clustering

| Field | Detail |
|-------|--------|
| **Full Citation** | S. Zhang & X. Liu, "Improving the functionality of wireless sensor networks through the use of reinforcement learning and metaheuristic-based energy efficient system," *Scientific Reports*, vol. 15, 30758, Aug. 2025. [DOI: 10.1038/s41598-025-16128-9](https://doi.org/10.1038/s41598-025-16128-9) |
| **Objective** | Combine Harris Hawks Optimization (HHO) for energy-aware clustering with RL-trained fuzzy logic for cluster head selection in WSNs[^5]. |
| **Methodology** | HHO performs clustering considering distance, dispersion, and energy balance. Fuzzy rules optimized via Wild Horse Optimization select CH with greatest remaining energy, fewest neighbours, and shortest path to BS[^6]. |
| **Key Results** | 29% increase in network lifetime and 46% increase in data volume delivered to the base station compared to LEACH[^5]. |
| **Limitations** | Multi-step optimization pipeline introduces computational complexity; not tested in disaster scenarios or with dynamic topology changes[^5]. |
| **Thematic Relevance** | Energy-efficient clustering, AI-based CH selection — extends to sustainability-oriented routing design. |

***

### A4. Parmar et al. (2025) — Survey on Intelligent Energy-Aware Routing

| Field | Detail |
|-------|--------|
| **Full Citation** | B. Parmar, S. Dabhi, K. Patel, V. Vohra & K. B. Dabhi, "State-of-the-Art Survey on Intelligent Energy-Aware Routing Algorithms in Wireless Sensor Networks," *International Journal of Technology & Emerging Research (IJTER)*, vol. 1, no. 6, pp. 52–57, 2025. [DOI: 10.64823/ijter.2506005](https://doi.org/10.64823/ijter.2506005) |
| **Objective** | Investigate AI-based routing techniques — including deep RL, fuzzy logic, swarm intelligence, and hybrid meta-heuristics — for dynamic path optimization in WSNs[^7]. |
| **Methodology** | Survey of current state-of-the-art algorithms with comparative performance analysis examining trade-offs in energy efficiency, latency, and computational cost[^7]. |
| **Key Results** | AI-driven routing significantly enhances network lifetime and data throughput over traditional approaches. Hybrid methods (combining RL with metaheuristics) show strongest performance[^7]. |
| **Limitations** | Does not address disaster-specific requirements, carbon-awareness, or environmental sustainability. Simulation-dominated; real-world validation gap acknowledged[^7]. |
| **Thematic Relevance** | Comprehensive survey contextualizing AI routing landscape — useful baseline for identifying gaps in carbon-aware routing. |

***

### A5. Mohammed et al. (2024) — Adaptive ACO + 6G for WSN Routing

| Field | Detail |
|-------|--------|
| **Full Citation** | H. S. Mohammed, O. A. Abdulkareem, A. Ahmad & C. S. Dowse, "Energy-Efficient Wireless Sensor Networks Using Adaptive Ant Colony Optimization and Sixth Generation (6G) Technology," *IJETT*, vol. 72, no. 10, pp. 90–95, Oct. 2024. [DOI: 10.14445/22315381/IJETT-V72I10P110](https://doi.org/10.14445/22315381/IJETT-V72I10P110) |
| **Objective** | Enhance energy efficiency in WSNs by integrating adaptive ACO with 6G technology for routing optimization[^8]. |
| **Methodology** | Adaptive ACO dynamically adjusts pheromone levels based on real-time network conditions. 6G technology provides ultra-low latency and high data rates for faster communication. Tested in mesh topology with 50 nodes in 1000×1000 area[^9]. |
| **Key Results** | Significantly outperforms traditional routing algorithms in energy conservation and network reliability. 6G integration enables faster and more efficient communication paths[^8]. |
| **Limitations** | Small-scale simulation only; no real 6G infrastructure tested. 6G aspects remain conceptual. No disaster or sustainability metrics[^9]. |
| **Thematic Relevance** | 6G integration with routing, energy efficiency — directly relevant to the 6G-integrated WSN pillar. |

***

### A6. WOAD3QN-RP (2024) — Whale Optimization + Deep RL Routing

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors not fully specified), "WOAD3QN-RP: An intelligent routing protocol in wireless sensor networks — A swarm intelligence and deep reinforcement learning based approach," *Expert Systems with Applications*, vol. 245, Jul. 2024. [Link](https://www.sciencedirect.com/science/article/abs/pii/S0957417423035911) |
| **Objective** | Address limitations of conventional WSN routing protocols by combining Whale Optimization Algorithm (WOA) for CH selection with Dueling Deep Q-Network (D3QN) for multi-hop path selection[^10]. |
| **Methodology** | WOA evaluates residual energy, node distances, and communication delays for CH selection. D3QN uses neural networks to adapt routing policies to dynamic topology changes[^10]. |
| **Key Results** | Effectively diminishes delays while balancing energy usage and adapting to topology changes. Identifies optimal multi-hop pathways for prolonged network longevity[^10]. |
| **Limitations** | Computational demands of deep RL may exceed resource-constrained sensor node capabilities. No edge offloading or disaster-specific evaluation[^10]. |
| **Thematic Relevance** | AI-based routing, deep RL for WSN — represents cutting-edge intelligent routing approach. |

***

### A7. Metaheuristic SLR for WSN Energy Optimization (2026)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Metaheuristic Approaches for Energy Optimization in Wireless Sensor Networks: A Systematic Review of Trends, Challenges, and Future Directions," *EAI Endorsed Transactions on Internet of Things*, vol. 12, Jan. 2026. [DOI: 10.4108/eetiot.10328](https://doi.org/10.4108/eetiot.10328) |
| **Objective** | Provide a holistic SLR of metaheuristic optimization (routing + clustering) in WSNs across 48 primary studies (2019–2024)[^11]. |
| **Methodology** | Systematic literature review with taxonomy integrating routing and clustering optimizations. Analyzes ACO, PSO, hybrid techniques (Firefly–PSO, GWO variants)[^11]. |
| **Key Results** | ACO and PSO each appear in 23.5% of studies. Shift toward hybrid techniques. Performance evaluations focus on energy consumption (31.2%), network lifetime (29.8%), throughput (19.9%). Real-world IIoT validations remain scarce[^11]. |
| **Limitations** | Identifies critical open issues in fault tolerance, heterogeneous node management, and security-aware routing. No carbon or lifecycle sustainability considerations[^11]. |
| **Thematic Relevance** | Comprehensive landscape of energy optimization in WSN routing — highlights gap for sustainability metrics. |

***

### A8. RPL Routing Protocol Evaluations

| Field | Detail |
|-------|--------|
| **Full Citation** | (i) A. Y. Barnawi, G. A. Mohsen & E. Q. Shahra, "Performance Analysis of RPL Protocol for Data Gathering Applications in WSNs," *Procedia Computer Science*, 2019. [Link](https://www.sciencedirect.com/science/article/pii/S1877050919304909); (ii) C. Lim, "A Survey on Congestion Control for RPL-Based WSNs," *Sensors*, vol. 19, no. 11, 2567, Jun. 2019. [DOI: 10.3390/s19112567](https://doi.org/10.3390/s19112567) |
| **Objective** | Evaluate RPL performance in IoT-WSNs and survey congestion control mechanisms for RPL-based networks[^12][^13]. |
| **Methodology** | Barnawi et al. analyze RPL across PDR, power consumption, and packet reception metrics. Lim reviews RPL congestion control schemes and load-balancing strategies[^13]. |
| **Key Results** | RPL is the de facto standard routing protocol for LLNs. Congestion can reduce network lifetime; multiple improvement schemes exist. RPL struggles under high density and mobility[^13][^14]. |
| **Limitations** | RPL does not natively support self-healing, carbon-awareness, or disaster-specific adaptation. Mobility support is limited[^14]. |
| **Thematic Relevance** | Baseline routing protocol for IoT-WSN — critical benchmark for comparing proposed routing approaches. |

***

### A9. Context-Aware Routing in IoT-Driven WSNs (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Advancing IoT-Driven WSNs with Context-Aware Routing: A Comprehensive Review," *Computer Science Review*, vol. 55, 2025. [Link](https://www.sciencedirect.com/science/article/abs/pii/S1574013725000796) |
| **Objective** | Present the first comprehensive review of context-aware routing protocols in IoT-driven WSNs, filling a critical research gap[^15]. |
| **Methodology** | Novel classification framework organizing protocols by operational context and network characteristics over two decades of research[^16]. |
| **Key Results** | Context-Aware Clustering Hierarchy (CACH) reduces energy by 58.8% vs. LEACH. CA-RPL achieves 50% less power consumption with 85–90% PDR under low mobility[^15]. |
| **Limitations** | Reactive and hybrid context-aware methods remain underexplored. No disaster-specific or carbon-aware context integration[^16]. |
| **Thematic Relevance** | Context-aware routing — potential integration point for carbon-intensity as a routing context parameter. |

***

## Section B: Self-Healing and Fault-Tolerant Routing

### B1. Shyama, Pillai & Anpalagan (2022) — FTGSO Self-Healing Routing

| Field | Detail |
|-------|--------|
| **Full Citation** | M. Shyama, A. S. Pillai & A. Anpalagan, "Self-healing and optimal fault-tolerant routing in wireless sensor networks using genetical swarm optimization," *Computer Networks*, vol. 217, Nov. 2022. [DOI: 10.1016/j.comnet.2022.109344](https://www.sciencedirect.com/science/article/pii/S1389128622003930) |
| **Objective** | Improve the self-healing capacity and fault tolerance of WSNs using a hybrid metaheuristic (Genetical Swarm Optimization = GA + PSO)[^17]. |
| **Methodology** | GSO-based CH selection (residual energy, coverage, communication cost, proximity). Fault-free routing path identified by GSO; self-healing method resolves connectivity issues[^17]. |
| **Key Results** | 96.8% PDR, 0.19 J energy consumption, 3.2% PLR, 30 ms E2E delay — outperforming existing optimization-based routing protocols[^17]. |
| **Limitations** | Evaluated in simulated single-fault scenarios; performance under simultaneous large-scale failures (as in earthquakes) not tested. No carbon or lifecycle metrics[^17]. |
| **Thematic Relevance** | Self-healing routing, fault tolerance — core reference for self-healing WSN pillar. |

***

### B2. Gayathri & Snigdha (2025) — SHEER Protocol

| Field | Detail |
|-------|--------|
| **Full Citation** | M. Gayathri & V. V. Snigdha, "Self-healing and energy-efficient cluster-based routing for sustainable wireless sensor networks," *Frontiers in Communications and Networks*, vol. 6, Jul. 2025. [DOI: 10.3389/frcmn.2025.1602928](https://doi.org/10.3389/frcmn.2025.1602928) |
| **Objective** | Develop clustering with integrated self-healing (SHEER) for CH selection considering energy, distance, and trust metrics[^18]. |
| **Methodology** | Dynamic CH/CM redistribution upon node failure; simulated in Cooja software with 100–500 sensor nodes[^18]. |
| **Key Results** | 98% PDR, 2% PLR, reduced energy consumption, stable cluster maintenance under node failures[^18]. |
| **Limitations** | "Sustainable" refers only to network lifetime, not environmental/lifecycle sustainability. No carbon footprint or disaster evaluation[^18]. |
| **Thematic Relevance** | Self-healing + energy-efficient routing — key gap: redefining "sustainability" to include carbon. |

***

### B3. Abba & Lee (2015) — ASAART

| Field | Detail |
|-------|--------|
| **Full Citation** | S. Abba & J.-A. Lee, "An Autonomous Self-Aware and Adaptive Fault Tolerant Routing Technique for Wireless Sensor Networks," *Sensors*, vol. 15, no. 8, pp. 20316–20354, Aug. 2015. [DOI: 10.3390/s150820316](https://doi.org/10.3390/s150820316) |
| **Objective** | Address limitations of self-healing routing (SHR) and self-selective routing (SSR) by integrating autonomic self-awareness and adaptive fault detection[^19]. |
| **Methodology** | Combined continuous and slotted prioritized back-off delays with multiple random functions for route formation and repair under transient and permanent failures[^19]. |
| **Key Results** | ASAART outperformed SHR and SSR across five scenarios with improved routing convergence, packet delivery, and energy conservation[^20]. |
| **Limitations** | Single-path recovery; no multi-path or redundancy strategies for large-area failures. No energy harvesting or sustainability integration[^19]. |
| **Thematic Relevance** | Autonomous self-aware routing, fault tolerance — foundational for autonomic disaster WSN design. |

***

### B4. FT-RR Protocol (2024) — Fault-Tolerant Reliable Routing

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Energy-efficient and fault-tolerant routing mechanism for WSN using optimizer based deep learning model," *Sustainable Computing: Informatics and Systems*, vol. 45, Dec. 2024. [Link](https://www.sciencedirect.com/science/article/abs/pii/S2210537924000891) |
| **Objective** | Develop a reliable and fault-tolerant routing protocol (FT-RR) that preemptively addresses sensor failures in WSNs[^21]. |
| **Methodology** | Bernoulli's principle identifies reliable nodes; connections established when CHs possess sufficient energy. Combined with deep learning-based optimizer[^21]. |
| **Key Results** | Surpasses existing protocols in packet loss rates, end-to-end latency, and overall network longevity[^21]. |
| **Limitations** | Pre-emptive fault tolerance assumes predictable failure patterns; does not model sudden disaster-induced destruction[^21]. |
| **Thematic Relevance** | Fault-tolerant routing, energy efficiency — complement to self-healing mechanisms. |

***

### B5. LEACH Protocol — Comprehensive Surveys

| Field | Detail |
|-------|--------|
| **Full Citation** | (i) M. B. Yassein et al., "A comprehensive survey on LEACH-based clustering routing protocols in Wireless Sensor Networks," *Ad Hoc Networks*, vol. 114, 2021. [Link](https://www.sciencedirect.com/science/article/abs/pii/S1570870520307356); (ii) M. A. Khan et al., "A comparative survey on LEACH successors clustering algorithms for energy-efficient longevity WSNs," *Arabian Journal for Science and Engineering*, 2024. [Link](https://research.uaeu.ac.ae/en/publications/a-comparative-survey-on-leach-successors-clustering-algorithms-fo/) |
| **Objective** | Provide in-depth evaluation of LEACH and its descendants for hierarchical clustering in WSNs[^22][^23]. |
| **Methodology** | Both papers classify LEACH variants by CH selection method, data transmission strategy, and hybrid approaches. Assess across energy efficiency, scalability, node mobility, and localization[^22]. |
| **Key Results** | LEACH and its variants remain the most widely used clustering protocols. Key improvements target: uneven CH distribution, energy imbalance, and lack of multi-hop support in the original protocol[^24][^23]. |
| **Limitations** | Original LEACH assumes homogeneous nodes, single-hop to BS, and no fault tolerance. Variants typically address one limitation at a time, not holistically[^22]. |
| **Thematic Relevance** | Foundational clustering protocol — baseline against which all improved CH selection methods are benchmarked. |

***

## Section C: Autonomous WSN and Self-Organizing Networks

### C1. Portocarrero et al. (2014) — Autonomic WSN SLR

| Field | Detail |
|-------|--------|
| **Full Citation** | J. M. T. Portocarrero, F. C. Delicato, P. F. Pires et al., "Autonomic Wireless Sensor Networks: A Systematic Literature Review," *Journal of Sensors*, vol. 2014, Art. 782789, Dec. 2014. [DOI: 10.1155/2014/782789](https://onlinelibrary.wiley.com/doi/10.1155/2014/782789) |
| **Objective** | Survey WSN middleware systems that implement autonomic computing self-* properties (self-configuration, self-optimization, self-healing, self-protection)[^25]. |
| **Methodology** | Systematic literature review identifying autonomic computing development approaches for WSN middleware[^26]. |
| **Key Results** | Self-configuration and self-optimization are most commonly addressed. Fewer studies tackle self-healing and self-protection. Middleware provides the necessary abstraction for autonomic behavior[^25]. |
| **Limitations** | Most studies address self-* properties in isolation; few integrate all four into a unified framework. No real-world disaster deployments[^25]. |
| **Thematic Relevance** | Autonomous WSN — foundational survey establishing gap for integrated autonomic frameworks. |

***

### C2. Secure and Fault-Tolerant AWSN Routing — East African Journal (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Secure and Fault-Tolerant Routing in Adaptive Wireless Sensor Networks: A Systematic Review," *East African Journal of Information Technology*, 2025. [Link](https://journals.eanso.org/index.php/eajit/article/download/4496/4951/) |
| **Objective** | Systematically review security mechanisms, fault-tolerance techniques, and adaptive routing in Adaptive WSNs (AWSNs)[^27]. |
| **Methodology** | Analyzed AWSN architectures, adaptive algorithms, security mechanisms, and fault-tolerance techniques including distributed self-healing and connectivity restoration[^27]. |
| **Key Results** | Current protocols address individual challenges (encryption, authentication, adaptive routing, failure recovery) but lack cross-layer integration. Lightweight cryptography and adaptive routing are promising but energy-intensive[^27]. |
| **Limitations** | Absence of integrated, cross-layer solutions simultaneously supporting security, fault tolerance, and adaptive routing[^27]. |
| **Thematic Relevance** | Autonomous WSN, self-healing, adaptive routing — highlights cross-layer integration gap. |

***

### C3. AI-Driven Self-Organizing Networks (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Self-organizing complex networks with AI-driven adaptive nodes for robust and energy-efficient performance," *Scientific Reports*, Dec. 2025. [Link](https://www.nature.com/articles/s41598-025-28035-0) |
| **Objective** | Develop an AI-enhanced self-organizing network model where each node autonomously adjusts connectivity for robustness and energy efficiency[^28]. |
| **Methodology** | Per-node AI-based decision-making dynamically adjusts transmission power and connections based on local topology and energy constraints[^28]. |
| **Key Results** | Improved network robustness, resilience to node failures, and efficient energy usage in large-scale simulations[^28]. |
| **Limitations** | Computational demands of per-node AI inference may exceed low-power sensor hardware. No carbon or lifecycle sustainability metrics[^28]. |
| **Thematic Relevance** | Self-organizing networks, AI-driven autonomy — relevant to autonomous disaster WSN design. |

***

## Section D: 6G Integration and Future Wireless Networks

### D1. 6G Network Slicing for IoT — Alwakeel & Alnaim (2024)

| Field | Detail |
|-------|--------|
| **Full Citation** | A. M. Alwakeel & A. K. Alnaim, "Network Slicing in 6G: A Strategic Framework for IoT in Smart Cities," *Sensors*, vol. 24, no. 13, 4254, Jun. 2024. [DOI: 10.3390/s24134254](https://pmc.ncbi.nlm.nih.gov/articles/PMC11243923/) |
| **Objective** | Develop an advanced network slicing framework for 6G smart city IoT deployments[^29]. |
| **Methodology** | Comprehensive methodology covering requirement analysis, metric formulation, constraint specification, mathematical modeling, and performance evaluation[^29]. |
| **Key Results** | Low RTT, minimal packet loss, increased availability, enhanced throughput. 256-bit encryption for security[^29]. |
| **Limitations** | Focused on smart city scenarios; disaster environments with destroyed infrastructure not addressed[^29]. |
| **Thematic Relevance** | 6G slicing for IoT — gap: no disaster-resilient slicing framework exists. |

***

### D2. Energy-Aware Intelligent Routing for 6G WSN (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Energy-aware intelligent routing framework for 6G-based wireless sensor networks," *Procedia Computer Science*, 2025. [Link](https://www.sciencedirect.com/science/article/pii/S1877050925014644) |
| **Objective** | Propose an intelligent Q-learning-based framework to efficiently determine energy-efficient routing paths between sensor nodes and sink in 6G-based WSNs[^30]. |
| **Methodology** | Q-learning-based routing algorithm adapted for 6G environment offering faster data speeds, ultra-low latency, greater connectivity, improved energy efficiency[^31]. |
| **Key Results** | 6G integration enables superior coverage and data rates compared to 5G for WSN applications[^30]. |
| **Limitations** | 6G infrastructure remains largely theoretical; no real 6G testbed validation. Disaster and carbon-awareness not addressed[^31]. |
| **Thematic Relevance** | 6G + AI routing — directly relevant to the 6G-integrated WSN pillar of the proposed research. |

***

### D3. Beyond-5G and 6G for Green IIoT — Varga et al. (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | P. Varga, Á. I. Jászberényi, D. Pásztor et al., "How Beyond-5G and 6G Makes IIoT and the Smart Grid Green — A Survey," *Sensors*, vol. 25, no. 13, 4222, Jul. 2025. [DOI: 10.3390/s25134222](https://doi.org/10.3390/s25134222) |
| **Objective** | Explore how beyond-5G and 6G technologies support greening of IIoT systems and smart grids[^32]. |
| **Methodology** | Survey covering energy-efficient communications, MIMO, IRS, energy harvesting, and AI-based network management for sustainable 6G[^32]. |
| **Key Results** | 6G enables new paradigms for sustainable IoT: native AI, THz bands, and semantic communication reduce energy per bit. COP26-aligned net-zero goals require holistic network optimization[^32]. |
| **Limitations** | Focused on IIoT/smart grid, not disaster monitoring. Carbon quantification remains at network-level, not device-level[^32]. |
| **Thematic Relevance** | 6G sustainability — bridges 6G with green networking goals; gap for disaster-specific greening. |

***

### D4. Greening IoE in 6G Networks — Al-Quzweeni et al. (2024)

| Field | Detail |
|-------|--------|
| **Full Citation** | A. Al-Quzweeni et al., "Towards Sustainable Industry 4.0: A Survey on Greening IoE in 6G Networks," *Sustainable Computing: Informatics and Systems*, vol. 44, Nov. 2024. [Link](https://www.sciencedirect.com/science/article/pii/S157087052400221X) |
| **Objective** | Provide comprehensive overview of how advanced technologies (Blockchain, Digital Twins, UAVs, ML) contribute to green IoE in 6G networks[^33]. |
| **Methodology** | Survey evaluating each technology's capability in greening IoE for Industry 4.0 applications, analyzing challenges and opportunities[^34]. |
| **Key Results** | Blockchain, DTs, UAVs, and ML each offer distinct energy efficiency gains. Hybrid approaches combining multiple technologies show strongest sustainability potential[^33]. |
| **Limitations** | Focuses on Industry 4.0 applications; disaster monitoring WSNs not considered. Carbon metrics remain high-level[^34]. |
| **Thematic Relevance** | Green 6G IoE — provides technology landscape for sustainable 6G integration. |

***

## Section E: Sustainability, Carbon-Awareness, and Lifecycle Assessment

### E1. Pirson & Bol (2021) — Embodied Carbon of IoT Edge Devices

| Field | Detail |
|-------|--------|
| **Full Citation** | T. Pirson & D. Bol, "Assessing the embodied carbon footprint of IoT edge devices with a bottom-up life-cycle approach," *Journal of Cleaner Production*, vol. 349, 2022. [arXiv:2105.02082](https://arxiv.org/abs/2105.02082) |
| **Objective** | Present a parametric LCA framework to evaluate the cradle-to-gate carbon footprint of IoT edge devices[^35]. |
| **Methodology** | Bottom-up LCA using hardware profiles; applied to four use cases. Macroscopic analysis estimates global production carbon footprint over 10-year period[^36]. |
| **Key Results** | Production carbon footprint between simple and complex IoT devices varies by >150×. Global IoT edge device production could reach 22–562 MtCO₂-eq/year by 2027; worst-case exceeds 1000 MtCO₂-eq/year with truncation correction[^35]. |
| **Limitations** | Cradle-to-gate only (excludes use phase and end-of-life). Generic hardware profiles may not capture WSN-specific designs[^36]. |
| **Thematic Relevance** | Embodied carbon, lifecycle assessment — foundational for lifecycle-sustainable sensor network design. |

***

### E2. Wagih (2024) — LCA of Wireless RF Systems

| Field | Detail |
|-------|--------|
| **Full Citation** | M. Wagih, A. Bainbridge, B. Alsulami et al., "Environmental Life-Cycle Assessment (LCA) of Wireless RF Systems," *IEEE Journal of Microwaves*, 2024. [Link](https://ieeexplore.ieee.org/iel8/9171629/10803549/10703165.pdf) |
| **Objective** | Present the first comparative LCA specific to RF and microwave applications with a design-for-sustainability guide[^37]. |
| **Methodology** | LCA of active microwave sensor systems; bespoke PCB model for surface finish and transmission line area. Analyzes phased arrays, filters, and antennas[^38]. |
| **Key Results** | ICs have the largest environmental impact (>80% of embodied carbon). CMOS process choice, PCB material, and surface finish significantly affect lifecycle impact. Design choices at mmWave frequencies introduce additional environmental trade-offs[^38]. |
| **Limitations** | Focused on individual RF components; does not model full-scale sensor network deployment or operational carbon from data transmission[^37]. |
| **Thematic Relevance** | Embodied carbon of wireless hardware — critical for lifecycle-sustainable WSN hardware design. |

***

### E3. Piastou (2026) — Carbon-Aware Scheduling

| Field | Detail |
|-------|--------|
| **Full Citation** | M. Piastou, "Green software development using carbon-aware scheduling techniques and energy efficiency metrics throughout the SDLC," *Latin-American Journal of Computing*, vol. 13, no. 1, Jan. 2026. [DOI: 10.33333/lajc.vol13n1.06](https://doi.org/10.33333/lajc.vol13n1.06) |
| **Objective** | Systematize carbon-aware scheduling approaches and energy efficiency metrics throughout the software development lifecycle[^39]. |
| **Methodology** | Analysis of peer-reviewed articles (2020–2025) identifying four strategies: temporal task shifting, geographic load migration, electricity price consideration, dynamic resource scaling[^40]. |
| **Key Results** | Carbon-aware scheduling can reduce application carbon footprint by 30–70% with moderate latency impact[^40]. |
| **Limitations** | Trade-offs between emission reduction and service quality not fully resolved. Metric standardization and carbon-intensity forecasting accuracy remain open challenges. Applied to cloud/data-center, not WSN/IoT[^39]. |
| **Thematic Relevance** | Carbon-aware computing — key gap: extending these principles to distributed sensor networks. |

***

### E4. Green IoT EAVM Protocol (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Energy-Aware Adaptive Virtualization and Migration Protocol for Green IoT WSNs," *Scientific Reports*, vol. 15, Dec. 2025. [Link](https://www.nature.com/articles/s41598-025-28783-z) |
| **Objective** | Address energy and sustainability challenges in large-scale Green IoT WSNs through adaptive virtualization[^41]. |
| **Methodology** | Federated Deep Reinforcement Learning (FDRL) combined with hybrid solar–RF energy harvesting for dynamic virtual resource allocation and migration[^41]. |
| **Key Results** | Enhanced energy efficiency, scalability, and sustainability relative to state-of-the-art Green IoT techniques[^41]. |
| **Limitations** | FDRL requires significant computational resources for training. Applicability to ultra-constrained disaster sensor nodes is questionable[^41]. |
| **Thematic Relevance** | Green IoT, energy harvesting, virtualization — bridges sustainability with WSN operation. |

***

### E5. LCA of Wireless ICT Networks — Ruiz et al. (2022)

| Field | Detail |
|-------|--------|
| **Full Citation** | D. Ruiz et al., "Life cycle inventory and carbon footprint assessment of wireless ICT networks," *Resources, Conservation and Recycling*, vol. 177, 2022. [Link](https://www.sciencedirect.com/science/article/pii/S0921344921005607) |
| **Objective** | Quantify the carbon footprint of 4G LTE networks across the full lifecycle (cradle-to-grave)[^42]. |
| **Methodology** | LCA covering extraction, manufacturing, transport, operation, and end-of-life for user devices, eNodeB, EPC, and data centers across six demographic scenarios[^42]. |
| **Key Results** | Embodied emissions are a significant and often underestimated portion of total network carbon. Urban deployments have lower per-user carbon than rural/remote due to infrastructure sharing[^42]. |
| **Limitations** | Focused on 4G LTE; does not extend to 5G/6G or WSN-specific deployments[^42]. |
| **Thematic Relevance** | Lifecycle carbon assessment — methodology template for applying LCA to disaster WSN deployments. |

***

## Section F: Disaster Monitoring with WSNs

### F1. Benkhelifa et al. — WSN Disaster Management Survey

| Field | Detail |
|-------|--------|
| **Full Citation** | I. Benkhelifa, N. Nouali-Taboudjemat & S. Moussaoui, "Disaster Management Projects Using Wireless Sensor Networks: An Overview," *Journal of Network and Computer Applications*. [Link](https://asjp.cerist.dz/en/downArticle/134/23/1/23926) |
| **Objective** | Survey recent WSN projects for disaster management and emergency response[^43]. |
| **Methodology** | Comprehensive review of WSN applications: air pollution, forest fire, landslide detection, water-level monitoring, earthquake vibration detection[^43]. |
| **Key Results** | WSNs offer cost-effective alternatives to traditional ad-hoc networks when infrastructure collapses. Multi-parameter monitoring improves detection accuracy[^43]. |
| **Limitations** | Most projects are pilot-scale; large-scale, long-term deployments face sustainability, maintenance, and reliability challenges[^43]. |
| **Thematic Relevance** | Disaster monitoring WSN — baseline survey for disaster application context. |

***

### F2. IJFMR (2024) — Multi-Disaster WSN System

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Wireless Sensor Network for Disaster Management," *International Journal for Multidisciplinary Research*, vol. 6, no. 6, 2024. [Link](https://ijfmr.com/papers/2024/6/31605.pdf) |
| **Objective** | Develop an integrated WSN for multi-disaster monitoring (floods, earthquakes, weather, gas hazards)[^44]. |
| **Methodology** | Water-level sensors, accelerometers, temperature/humidity sensors, gas sensors connected to a central monitoring station[^45]. |
| **Key Results** | Flood sensors accurately identified rising water levels; accelerometers captured seismic activity; system generated real-time alerts[^44]. |
| **Limitations** | Minor data transmission issues in high-interference areas. No data reduction, energy-efficient routing, or self-healing capability[^44]. |
| **Thematic Relevance** | Multi-hazard disaster monitoring — illustrates gap for energy-efficient and self-healing disaster WSNs. |

***

### F3. Adaptive Landslide Monitoring — FLPSO (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | L. K et al., "Adaptive landslide monitoring in wireless sensor networks using FLPSO-based MIP systems," *Results in Engineering*, vol. 25, Art. 104329, Mar. 2025. [Link](https://www.sciencedirect.com/science/article/pii/S2590123025004104) |
| **Objective** | Introduce a Fuzzy Logic-based Particle Swarm Optimization (FLPSO) itinerary planning approach for energy-efficient landslide detection in WSNs[^46]. |
| **Methodology** | FLPSO integrates fuzzy logic and PSO for energy optimization. Case study in Shiradi village, Mangalore, India. One year of field data collection[^47]. |
| **Key Results** | 14.15% improvement in PDR, 11.15% in Energy Delay Product, 10.15% in PLR, 22.1% in task delay, 20.1% in throughput vs. existing methods[^46]. |
| **Limitations** | Single-hazard (landslide only); no multi-hazard integration. No self-healing or carbon-aware operation[^46]. |
| **Thematic Relevance** | Disaster monitoring + energy-efficient routing — demonstrates field-validated WSN for natural disaster. |

***

### F4. Self-Healing Emergency Networks (2026)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Self-Healing Networks for Disaster Management," Scribd Document, Feb. 2026. [Link](https://www.scribd.com/document/963382587/12) |
| **Objective** | Analyze architectures and technologies for self-healing emergency communication networks[^48]. |
| **Methodology** | Review of wireless mesh networks, AI-based routing algorithms (DSR, AODV), and edge computing integration for fault tolerance[^48]. |
| **Key Results** | Self-healing networks demonstrated significant improvement in communication reliability during simulated disaster scenarios. AI routing optimized transmission and prevented congestion[^48]. |
| **Limitations** | Primarily theoretical; real-world disaster validation limited. Energy/carbon costs of AI routing on battery-powered nodes not evaluated[^48]. |
| **Thematic Relevance** | Self-healing + disaster management — directly relevant but lacks sustainability analysis. |

***

### F5. Flood Monitoring with ZigBee IoT (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Disaster management-based internet of things using wireless sensor networks," *Engineering and Technology Journal*, 2025. [Link](https://etj.uotechnology.edu.iq/article_188841.html) |
| **Objective** | Develop a flood monitoring system using WSN with ZigBee and IoT integration for dam water-level monitoring[^49]. |
| **Methodology** | Water-level sensors in dam basements using ZigBee for low-power transmission to a base station with IoT-enabled mobile alerts[^50]. |
| **Key Results** | Accurate real-time water level variation detection. ZigBee provides enhanced energy efficiency, scalability, and range[^50]. |
| **Limitations** | Single-hazard (flood) only. No self-healing, multi-hazard integration, or sustainability metrics[^50]. |
| **Thematic Relevance** | Disaster monitoring + IoT — typical current-generation disaster WSN lacking advanced features. |

***

## Section G: Routing Optimization — Comprehensive Surveys

### G1. WSN Routing Protocols Review (2025)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "WSN Routing Protocols: A Clear and Comprehensive Review," *Int. J. Advanced Natural Sciences and Engineering Researches*, vol. 9, no. 3, pp. 1–14, Feb. 2025. [DOI: 10.5281/zenodo.14957401](https://doi.org/10.5281/zenodo.14957401) |
| **Objective** | Provide a broader classification of WSN routing protocols by integrating multiple taxonomies (network structure, data delivery, path establishment, application type, next-hop selection)[^51]. |
| **Methodology** | Structured review merging diverse classification schemes into a unified framework[^51]. |
| **Key Results** | Key routing challenges identified: energy efficiency, scalability, and security. Unified taxonomy aids protocol comparison[^51]. |
| **Limitations** | Descriptive; no experimental validation. Does not cover disaster-specific or carbon-aware routing[^51]. |
| **Thematic Relevance** | General WSN routing taxonomy — useful reference framework for positioning proposed protocol. |

***

### G2. Routing Optimization in WSNs under IoT Framework (2026)

| Field | Detail |
|-------|--------|
| **Full Citation** | (Authors), "Routing Optimization and Challenges in Wireless Sensor Networks under IoT Framework," *Zenodo*, Feb. 2026. [Link](https://zenodo.org/records/18636074) |
| **Objective** | Comprehensive review of routing optimization covering ACO, PSO, GA, fuzzy logic, RL, deep learning, SDN-enabled IoT, edge/fog-assisted, and blockchain-based routing[^52]. |
| **Methodology** | Summarizes and compares representative protocols and solutions (2020–2025) across design goals, performance metrics, and application domains[^52]. |
| **Key Results** | Identifies trend toward self-optimizing, sustainable, and trustworthy routing. AI and edge computing integration emerge as dominant future directions[^52]. |
| **Limitations** | Sustainability discussed conceptually; no quantitative carbon or lifecycle metrics. Disaster-specific routing not covered[^52]. |
| **Thematic Relevance** | State-of-the-art routing landscape — positions the proposed carbon-aware approach within current trends. |

***

## Summary of Cross-Cutting Gaps

| Gap Identified | Sections Affected | Status |
|---------------|-------------------|--------|
| **No carbon-aware routing in WSNs** — all routing optimizes energy/latency, never carbon intensity | A, B, D | Completely unaddressed in WSN literature[^39][^11] |
| **"Sustainable" = network lifetime only** — no environmental lifecycle meaning | B2, E | SHEER[^18], EAVM[^41] use "sustainable" without carbon metrics |
| **Self-healing not tested under correlated disaster failures** — only random/single faults | B1, B3, F | FTGSO[^17], ASAART[^19] use simulated isolated faults |
| **No 6G integration with disaster WSN tiers** — 6G slicing targets smart cities | D1, D2, F | 6G WSN papers conceptual[^29][^30]; disaster WSNs use ZigBee/LoRa[^50] |
| **Embodied carbon studied at component level only** — no full disaster network LCA | E1, E2, E5 | Pirson[^35] covers IoT devices; Wagih[^37] covers RF; no end-to-end WSN deployment model |
| **AI routing computational cost ignored for constrained nodes** | A1, A2, A6, C3 | Deep RL and per-node AI exceed MCU capabilities[^28][^10] |
| **Disaster WSNs lack data reduction** — raw data transmitted | F2, F5 | No surveyed disaster system integrates compression or prediction[^44][^50] |
| **Circular economy absent from WSN hardware design** | E | Discussed for consumer electronics only; not for sensor node modularity or repairability |

---

## References

1. [AI-based routing algorithms improve energy efficiency, latency ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12216685/) - This paper proposes a modular Artificial Intelligence (AI)-based routing framework for Wireless Sens...

2. [AI-based routing algorithms improve energy efficiency, latency, ...](https://d-nb.info/1375721607/34)

3. [Energy-Efficient Routing Algorithm for Wireless Sensor Networks](https://arxiv.org/abs/2508.14679) - This paper presents a novel method using reinforcement learning-based cluster-head selection and a h...

4. [Energy-Efficient Routing Algorithm for Wireless Sensor Networks: A Multi-Agent Reinforcement Learning Approach](https://arxiv.org/abs/2508.14679v1) - Efficient energy management is essential in Wireless Sensor Networks (WSNs) to extend network lifeti...

5. [Improving the functionality of wireless sensor networks through the ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12370893/) - To improve the routing and data transmission of wireless sensor networks, this study recommends util...

6. [Improving the functionality of wireless sensor networks ... - Nature](https://www.nature.com/articles/s41598-025-16128-9) - Efficient energy utilization in wireless sensor networks can be achieved by intelligent routing and ...

7. [State-of-the-Art Survey on Intelligent Energy-Aware ...](https://www.ijter.org/article/212509271086/state-of-the-art-survey-on-intelligent-energy-aware-routing-algorithms-in-wireless-sensor-networks) - Wireless Sensor Networks (WSNs) are vital for applications such as environmental monitoring and indu...

8. [Energy-Efficient Wireless Sensor Networks Using Adaptive Ant ...](https://demo.ijettjournal.org/archive/ijett-v72i10p110) - This paper introduces an innovative method for enhancing energy efficiency in Wireless Sensor Networ...

9. [Energy-Efficient Wireless Sensor Networks Using Adaptive Ant Colony Optimization and Sixth Generation (6G) Technology](https://ijettjournal.org/Volume-72/Issue-10/IJETT-V72I10P110.pdf)

10. [WOAD3QN-RP: An intelligent routing protocol in wireless sensor networks — A swarm intelligence and deep reinforcement learning based approach ☆](https://www.sciencedirect.com/science/article/abs/pii/S0957417423035911) - Wireless Sensor Networks (WSN) are a crucial part of the Internet of Things (IoT), and research on W...

11. [Metaheuristic Approaches for Energy Optimization in Wireless ...](https://publications.eai.eu/index.php/IoT/article/view/10328) - Wireless Sensor Networks (WSNs) have become a foundational technology across diverse domains, rangin...

12. [Performance Analysis of RPL Protocol for Data Gathering Applications in Wireless Sensor Networks](https://www.sciencedirect.com/science/article/pii/S1877050919304909)

13. [A Survey on Congestion Control for RPL-Based Wireless Sensor ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC6603919/) - In this survey, we review the RPL schemes proposed for congestion control and load-balancing and dis...

14. [Performance Evaluation of RPL in Wireless Sensor Networks ...](https://journals.tasued.edu.ng/index.php/vas/article/view/142) - Over time, wireless sensor networks (WSNs) have attracted significant research interest. These netwo...

15. [Review article Advancing IoT-driven WSNs with context-aware routing: A comprehensive review](https://www.sciencedirect.com/science/article/abs/pii/S1574013725000796) - With the increasing complexity of dynamic and heterogeneous IoT-driven Wireless Sensor Networks (WSN...

16. [Advancing IoT-driven WSNs with context-aware routing: A ...](https://nchr.elsevierpure.com/en/publications/advancing-iot-driven-wsns-with-context-aware-routing-a-comprehens/)

17. [Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization](https://www.sciencedirect.com/science/article/pii/S1389128622003930) - A wireless sensor network (WSN) is used in area monitoring, surveillance, virtual reality, artificia...

18. [Frontiers | Self-healing and energy-efficient cluster-based routing for sustainable wireless sensor networks](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2025.1602928/full) - Wireless sensor networks (WSNs) are extensively employed in various applications like environmental ...

19. [An Autonomous Self-Aware and Adaptive Fault Tolerant Routing Technique for Wireless Sensor Networks](https://pmc.ncbi.nlm.nih.gov/articles/PMC4570424/) - We propose an autonomous self-aware and adaptive fault-tolerant routing technique (ASAART) for wirel...

20. [An Autonomous Self-Aware and Adaptive Fault Tolerant Routing ...](https://ouci.dntb.gov.ua/en/works/4zzGYGP4/) - We propose an autonomous self-aware and adaptive fault-tolerant routing technique (ASAART) for wirel...

21. [Energy-efficient and fault-tolerant routing mechanism for WSN using optimizer based deep learning model](https://www.sciencedirect.com/science/article/abs/pii/S2210537924000891) - Fault tolerance is the network's capacity to continue operating normally in the event of sensor fail...

22. [A comprehensive survey on LEACH-based clustering routing ...](https://www.sciencedirect.com/science/article/abs/pii/S1570870520307356) - The LEACH protocol decreased the energy consumption in WSNs. In this survey, we provide a comprehens...

23. [A comparative survey on LEACH successors clustering ...](https://research.uaeu.ac.ae/en/publications/a-comparative-survey-on-leach-successors-clustering-algorithms-fo/)

24. [Low-energy adaptive clustering hierarchy - Wikipedia](https://en.wikipedia.org/wiki/Low-energy_adaptive_clustering_hierarchy)

25. [Autonomic Wireless Sensor Networks: A Systematic Literature Review](https://onlinelibrary.wiley.com/doi/10.1155/2014/782789) - In this systematic literature review (SLR) we aim to provide an overview of existing WSN middleware ...

26. [Autonomic Wireless Sensor Networks: A Systematic Literature Review](https://www.academia.edu/48342966/Autonomic_Wireless_Sensor_Networks_A_Systematic_Literature_Review) - Autonomic computing (AC) is a promising approach to meet basic requirements in the design of wireles...

27. [[PDF] East African Journal of Information Technology](https://journals.eanso.org/index.php/eajit/article/download/4496/4951/)

28. [Self-organizing complex networks with AI-driven adaptive nodes for ...](https://www.nature.com/articles/s41598-025-28035-0) - In this study, we introduce an Artificial Intelligence (AI)-enhanced self-organizing network model, ...

29. [Network Slicing in 6G: A Strategic Framework for IoT ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC11243923/) - The emergence of 6G communication technologies brings both opportunities and challenges for the Inte...

30. [Energy-aware intelligent routing framework for 6G-based wireless ...](https://www.sciencedirect.com/science/article/pii/S1877050925014644) - An intelligent Q-learning-based framework is proposed to efficiently determine energy-efficient rout...

31. [Energy-aware intelligent routing framework for 6G-based wireless ...](https://www.sciencedirect.com/science/article/pii/S1877050925014644/pdf?md5=3f22df24c5e7ffa3c2ed8136c74459c5&pid=1-s2.0-S1877050925014644-main.pdf) - 6G offers faster data speeds, ultra-low latency, greater connectivity, improved energy efficiency, a...

32. [How Beyond-5G and 6G Makes IIoT and the Smart Grid Green—A ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12252317/) - This survey explores how beyond-5G and 6G communication technologies can support the greening of Ind...

33. [A survey on greening IoE in 6G networks](https://www.sciencedirect.com/science/article/pii/S157087052400221X) - This survey provides a comprehensive overview of how advanced technologies can contribute to green I...

34. [Towards Sustainable Industry 4.0: A Survey on Greening the Ioe in 6g Networks](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4805495) - The dramatic recent increase of the smart Internet of Everything (IoE) in Industry 4.0 has significa...

35. [Assessing the embodied carbon footprint of IoT edge ...](https://arxiv.org/abs/2105.02082) - In this paper, we present a parametric framework based on hardware profiles to evaluate the cradle-t...

36. [[PDF] Assessing the embodied carbon footprint of IoT edge devices with a ...](https://arxiv.org/pdf/2105.02082.pdf) - A methodology to assess the direct environmental impacts of wireless sensors networks (WSN) is prese...

37. [Environmental Life-Cycle Assessment (LCA) of Wireless ...](https://ieeexplore.ieee.org/iel8/9171629/10803549/10703165.pdf) - by M Wagih · 2024 · Cited by 14 — In an active microwave system, over 80% of the embodied carbon (du...

38. [[PDF] Mahmoud Wagih1, Andrew Bainbridge1, Bashayer Alsulami1, and ...](https://d197for5662m48.cloudfront.net/documents/publicationstatus/212079/preprint_pdf/9f44aee1a5961a31f469b5b3d848a805.pdf)

39. [Green software development using Carbon-Aware Scheduling ...](https://lajc.epn.edu.ec/index.php/LAJC/article/view/463) - The objective of the present paper is to systematize contemporary approaches of green software devel...

40. [[PDF] Green software development using carbon-aware scheduling ...](https://lajc.epn.edu.ec/index.php/LAJC/article/download/463/351/2048)

41. [Energy-Aware adaptive virtualization and migration protocol for ...](https://www.nature.com/articles/s41598-025-28783-z) - The primary objective of this study is to present an EAVM protocol for Green IoT Wireless Sensor Net...

42. [[PDF] Life cycle inventory and carbon footprint assessment of wireless ICT ...](https://wiki.ietf.org/1-s2.0-s0921344921005607-main.pdf)

43. [[PDF] Disaster Management Projects using Wireless Sensor Networks](https://asjp.cerist.dz/en/downArticle/134/23/1/23926)

44. [International Journal for Multidisciplinary Research (IJFMR)](https://ijfmr.com/papers/2024/6/31605.pdf)

45. [[PDF] Wireless Sensor Network for Disaster Management - IJFMR](https://www.ijfmr.com/papers/2024/6/31605.pdf) - A network of wireless sensors that measures water level to check or to update related to floods, det...

46. [Adaptive landslide monitoring in wireless sensor networks using ...](https://researcher.manipal.edu/en/publications/adaptive-landslide-monitoring-in-wireless-sensor-networks-using-f/) - The primary objective of this approach is to minimize the energy consumption in large-scale WSNs, th...

47. [[PDF] Adaptive landslide monitoring in wireless sensor networks using ...](https://www.um.edu.mt/library/oar/bitstream/123456789/136810/1/Adaptive%20landslide%20monitoring%20in%20wireless%20sensor%20networks%20using%20FLPSO%20based%20MIP%20systems%202025.pdf) - Develop an Energy-Efficient Landslide Monitoring System: Design and implement a Wireless Sensor Netw...

48. [Self-Healing Networks for Disaster Management | PDF - Scribd](https://www.scribd.com/document/963382587/12) - Communication, Wireless Mesh Network, Disaster healing or corrective action happens autonomously.

49. [Disaster management-based internet of things using wireless ...](https://etj.uotechnology.edu.iq/article_188841.html) - This paper proposes a flood monitoring system based on a wireless sensor network, emphasizing instal...

50. [Disaster management-based internet of things using ...](https://doaj.org/article/07fefa00ddd2431ab45030b73a1bf92f) - Wireless Sensor Networks (WSNs) have become essential in the monitoring and managing environmental d...

51. [WSN Routing Protocols: A Clear and Comprehensive Review](https://as-proceeding.com/index.php/ijanser/article/view/2486) - This paper provides a comprehensive yet concise review of WSN routing protocols, offering a broader ...

52. [Routing Optimization and Challenges in Wireless Sensor Networks ...](https://zenodo.org/records/18636074) - Wireless Sensor Networks (WSNs) constitute a key enabling technology for the Internet of Things (IoT...


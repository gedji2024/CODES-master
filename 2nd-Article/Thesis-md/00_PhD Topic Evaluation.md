# Academic Evaluation: "Autonomous Sustainable Data Reduction and Self-Healing Routing for 6G-Integrated Wireless Sensor Networks in Disaster Monitoring"

## Executive Summary

This evaluation assesses the proposed PhD topic by examining each constituent research component against current literature, identifying how they combine in existing work, pinpointing genuine research gaps, and suggesting refined topic phrasings. The topic sits at the intersection of eight active research threads—data reduction in WSNs, autonomous/zero-touch networks, network slicing, self-healing mechanisms, adaptive routing, 6G integration, sustainability/circular economy, and disaster monitoring. While each component is well-studied individually, the full integration of all eight dimensions—particularly the coupling of sustainability-aware data reduction with self-healing routing under 6G network slicing for disaster scenarios—represents a largely unexplored design space with strong novelty potential.

***

## Part 1: State of Each Component in Current Research

### Data Reduction Mechanisms in WSNs

Data reduction is one of the most extensively studied energy management strategies in WSNs. Techniques span adaptive sampling, in-network data aggregation, compressive sensing, data prediction, and data fusion. A comprehensive 2023 survey by Jain et al. catalogued data transmission reduction techniques from 2017–2022, documenting filter-based, tree-based, cluster-based, and data-stream-based methods. More recent work (2025) introduces hybrid approaches combining adaptive sampling, compressive sensing, and hierarchical clustering with reinforcement learning to dynamically adjust sampling parameters, achieving 37.8% energy reduction while maintaining 94.2% reconstruction accuracy. A novel compressive sensing paradigm (NSPL-HCS) further integrates enhanced PSO with Smoothed Projected Landweber reconstruction for joint energy and memory optimization in IoT networks. Semantic communication has also emerged as a 6G-native data reduction paradigm, transmitting only task-relevant information rather than raw data, effectively reframing data reduction at the meaning level.[^1][^2][^3][^4][^5][^6][^7]

**Maturity assessment:** Very mature field with extensive literature. Remaining gaps lie in context-aware, disaster-specific data reduction and integration with next-generation (6G) network capabilities.

### Autonomous Networks

Autonomous networking has become a central pillar of 6G vision documents. The ETSI Zero-touch network and Service Management (ZSM) framework defines networks with self-configuration, self-monitoring, self-healing, self-optimization, and self-protection capabilities without human intervention. Nokia's 2025 white paper on cognitive autonomous 6G networks describes the transition from fragmented reactive automation to agent-driven cognitive autonomy, where networks reason, learn, predict, and act proactively. China Mobile targets Level 4 autonomous networks by 2025 with "Zero-touch, Zero-wait, Zero-trouble, Self-configuring, Self-healing, and Self-optimizing" capabilities. AI-native integrated sensing and communication (ISAC) for self-organizing wireless networks further demonstrates how ML-driven self-organization achieves autonomous topology adaptation and resource optimization.[^8][^9][^10][^11][^12]

**Maturity assessment:** Rapidly maturing at the macro-network level (5G/6G core). Under-explored at the WSN/IoT edge, where resource constraints impose unique challenges for autonomous decision-making.

### Network Slicing / Differentiated Networks

Network slicing is a well-established 5G technology now being extended for 6G. Alwakeel & Alnaim (2024) proposed an advanced 6G network slicing framework for IoT in smart cities with demonstrated efficiency in RTT, packet loss, and throughput. AI-native network slicing architectures integrate SAGIN (Space-Air-Ground Integrated Networks) with ubiquitous intelligence for diverse QoS requirements using SDN controllers and reinforcement learning for dynamic resource reservation. Recent work addresses dynamic soft slicing for 6G, formulating slice resource management as MILP optimization to balance utilization and QoS guarantees. In the disaster/PPDR domain, network slicing has been demonstrated for mission-critical communications, with dedicated slices guaranteeing bandwidth, latency, and reliability for emergency services.[^13][^14][^15][^16][^17][^18]

**Maturity assessment:** Well-developed for macro 5G/6G networks. Application to fine-grained WSN-level slice management for heterogeneous disaster sensor data is nascent.

### Self-Healing WSN

Self-healing in WSNs derives from biologically-inspired autonomic computing concepts (self-configuration, self-healing, self-optimization, self-protection). Shyama et al. (2022) proposed fault-tolerant routing with genetical swarm optimization (FTGSO), achieving 96.8% PDR and 0.19 J energy consumption through GSO-based fault-free routing paths. Gayathri & Snigdha (2025) introduced SHEER (Self-Healing and Energy-Efficient Cluster-based Routing), integrating trust metrics and dynamic CH redistribution upon node failure, achieving 98% PDR with 500-node simulations. A self-healing approach combining SCR and SCR-DTRA algorithms achieves fault-tolerant data aggregation through trust-based node selection and adaptive recovery. At the 6G level, Hegde et al. (2025) demonstrated autonomous self-healing UAV swarms (RASHND) for 6G non-terrestrial networks, using distributed combining techniques (d-MRC, d-LMMSE, SC) with state-machine-based algorithm switching validated on real SDR testbeds and UAV platforms.[^19][^20][^21][^22][^23][^24]

**Maturity assessment:** Active research area. Most works address either WSN-level or 6G-infrastructure-level self-healing, but rarely bridge both layers in an integrated cross-layer framework.

### Adaptive Routing Strategies

Adaptive routing in WSNs is a well-studied domain encompassing energy-aware, QoS-aware, and mobility-aware protocols. Recent advances include ML-driven routing frameworks using supervised learning, reinforcement learning, and regression for intelligent path selection based on node energy, congestion, and security. Multi-agent reinforcement learning (MARL) approaches model each sensor node as an autonomous agent making forwarding decisions based on residual energy, distance, hop count, and hotspot proximity. Abbas et al. (2024) developed an adaptive clustering protocol for fire emergencies using hybrid CNN-BiLSTM models for early fire prediction and adaptive data routing. For 5G/6G WSNs specifically, RL-based cluster head selection with data fusion techniques has been proposed, integrating mmWave path loss modeling, massive MIMO beamforming, and network slicing. Adaptive location-based routing for dynamic urban WSNs (UALRP) integrates real-time data analytics and ML for optimizing routing under continuously changing conditions.[^25][^26][^27][^28][^29]

**Maturity assessment:** Highly active. Gap exists in routing protocols that simultaneously adapt to disaster dynamics, manage heterogeneous 6G links, and integrate sustainability constraints.

### 6G Integration with WSNs/IoT

The convergence of WSNs with 6G is an emerging research frontier. A 2025 survey by IJRASET synthesizes innovations in WSN architecture, communication, energy harvesting, and AI/ML at the edge within the 6G context, identifying integration of WSNs with blockchain, edge computing, and green energy systems as key future directions. 6G promises ultra-low latency, terahertz bands, AI-native operation, integrated sensing and communication (ISAC), and massive connectivity (10⁶–10⁸ devices/km²) that fundamentally reshape WSN design. The AMAZING6G EU project specifically targets B5G/6G PPDR network slices with edge computing for disaster response. Semantic edge computing and semantic communications represent a 6G-native paradigm that reduces data volume by transmitting only semantic-level information, directly relevant to WSN data reduction.[^30][^31][^18][^7][^32]

**Maturity assessment:** Early-stage but rapidly growing. Most work is visionary or focuses on specific 6G enablers (RIS, ISAC, semantic communication) rather than holistic WSN integration frameworks.

### Sustainability, Energy Efficiency, Embodied Carbon, and Circular Economy

Sustainability in wireless networks spans operational energy efficiency, embodied carbon of equipment, circular economy practices, and renewable energy integration. A 2025 OECD report examines how extending equipment life, reuse/repurposing, recycling, and green supply chains contribute to network sustainability. The CHEDDAR white paper on carbon-neutral 6G networks introduces metrics including Total Carbon Emissions (TCE), Network Carbon Intensity (NCIe), and Renewable Energy Utilisation Rate (REUR), alongside carbon-aware decision engines for 6G. The GSMA circular economy strategy for network equipment emphasizes CO₂ savings through reuse, refurbishment, and lifecycle management. Aalto University's 2025 thesis provides comprehensive LCA of ICT equipment, finding that up to 80% of emissions come from manufacturing, highlighting the critical importance of embodied carbon. Ericsson's 2024 work and the Fraunhofer IIS 6G sustainability white paper further develop energy efficiency and carbon intensity KPIs. For WSNs specifically, energy harvesting (solar, thermal, RF) enables green self-sustaining nodes, and efficient green protocols have been taxonomized for sustainable WSN design.[^33][^34][^35][^36][^37][^31][^38][^39][^40][^41]

**Maturity assessment:** Rapidly growing at the macro-network level. Embodied carbon and circular economy considerations are almost entirely absent from WSN-specific literature—a significant gap.

### Disaster / Dynamic Monitoring Applications

WSNs are widely deployed for disaster monitoring including flood detection, earthquake early warning, wildfire tracking, and environmental hazard sensing. IoT-enabled WSN path planning for disaster management has been comprehensively reviewed, emphasizing real-time data collection and adaptive response. Digital twin technology enhances disaster preparedness with 28% improved forecast accuracy and 35% faster recovery times. 5G/6G network slicing for PPDR has been demonstrated in real deployments guaranteeing QoS for first-responder services. Adaptive priority scheduling of IoT data for disaster monitoring reduces urgent data transmission delays by 31%. An emergency response automation framework employs a 6G-blockchain communication layer for cross-organizational disaster coordination.[^42][^43][^16][^44][^45][^46][^47][^18]

**Maturity assessment:** Well-established application domain. Gaps exist in holistic system design that combines advanced data reduction, self-healing, 6G capabilities, and sustainability awareness specifically for disaster scenarios.

***

## Part 2: Existing Multi-Component Combinations and Identification of Rare/Absent Intersections

### Documented Combinations (Two or More Components)

| Combination | Representative Work | Status |
|---|---|---|
| Self-healing + Energy-efficient routing (WSN) | SHEER protocol: self-healing cluster-based routing with energy optimization[^22] | Well-studied |
| Data aggregation + Routing (WSN) | FABC-based routing with HFQKLMS data aggregation[^48]; comprehensive survey of data aggregation routing protocols[^49] | Very well-studied |
| Self-healing + 6G (NTN) | RASHND: autonomous self-healing UAV swarms for 6G non-terrestrial networks[^23] | Emerging (2025) |
| Network slicing + Disaster/PPDR | 5G network slicing for PPDR communications with guaranteed QoS[^17][^16] | Active |
| Network slicing + 6G + IoT | AI-native network slicing for 6G with SAGIN and diverse QoS[^14]; 6G IoT slicing framework[^13] | Active |
| RL-based routing + Energy efficiency (WSN) | Multi-agent RL routing with Q-learning for energy-aware WSN[^29][^50] | Active |
| Adaptive routing + Disaster | CNN-BiLSTM adaptive routing for fire emergencies[^26]; priority scheduling for disaster IoT[^42] | Emerging |
| Sustainability/Carbon + 6G | Carbon-neutral 6G white paper with carbon-aware decision engines[^31]; 6G energy efficiency framework[^39] | Active |
| Energy harvesting + WSN sustainability | Advances in EH-WSNs with routing, cognitive radio, and security[^34][^51] | Well-studied |
| Data reduction + Energy efficiency (WSN) | Compressive sensing + adaptive sampling + RL for 37.8% energy reduction[^4]; NSPL-HCS framework[^5] | Well-studied |
| Autonomous/ZSM + Self-healing (6G) | ETSI ZSM with self-healing capabilities; LLM-augmented zero-touch management[^52][^9] | Active |
| 5G/6G routing + WSN + Energy | CEERP protocol with mmWave, MIMO, slicing, and energy-aware clustering[^27] | Emerging |
| Self-healing + Data aggregation (WSN) | SCR-DTRA: self-healing fault-tolerant data aggregation[^24] | Limited |
| Semantic communication + 6G + Data reduction | Semantic edge computing and semantic communications survey[^7][^6] | Active |
| Digital twin + Disaster + IoT | Digital risk twins for disaster management integrating IoT and remote sensing[^46][^53] | Emerging |

### Rare or Absent Combinations

| Missing Combination | Assessment |
|---|---|
| **Data reduction + Self-healing routing + 6G integration** | No integrated framework found. Existing works treat these in separate silos. |
| **Sustainability (embodied carbon/circular economy) + WSN design** | Almost entirely absent. Sustainability in WSN literature focuses on operational energy, not lifecycle or embodied carbon. |
| **Network slicing + WSN-level data differentiation + Disaster monitoring** | Slicing exists at macro-network level for PPDR, but per-sensor or per-data-type slice management for heterogeneous disaster data is unexplored. |
| **Autonomous self-healing + Sustainability-aware routing in WSN** | Self-healing protocols do not incorporate carbon-aware or lifecycle-aware decision-making. |
| **Semantic data reduction + Self-healing + Disaster WSN** | Semantic communication is studied for 6G but never applied to disaster WSN self-healing contexts. |
| **Carbon-aware 6G + WSN edge + Disaster scenarios** | Carbon-aware 6G focuses on base stations and core networks, not on integrated WSN-edge-6G carbon optimization in disaster deployments. |
| **Full integration: Data reduction + Self-healing + 6G + Sustainability + Disaster** | **Completely absent.** This is the central novelty claim of the proposed topic. |

***

## Part 3: Illustrative Key Papers by Component

### Data Reduction in WSNs

- **Jain et al. (2023)** — "Data transmission reduction techniques for improving network lifetime in wireless sensor networks: An up-to-date survey from 2017 to 2022," *Transactions on Emerging Telecommunications Technologies*, 34(2), e4674. Comprehensive survey covering filtering, compression, prediction, and aggregation techniques.[^3]
- **Balamurali et al. (2025)** — "Redefining IoT networks for improving energy and memory efficiency through compressive sensing paradigm," *Scientific Reports*, 15, 27180. Novel NSPL-HCS framework integrating PSO with compressive sensing for joint energy-memory optimization.[^5]
- **Morphpublishing (2025)** — "Energy Conservation through Efficient Data Collection and Processing Techniques in Resource-Constrained WSNs," *JCIMRD*, 10(2), 21–37. Hybrid adaptive sampling, compressive sensing, and RL-based dynamic parameter adjustment achieving 37.8% energy reduction.[^4]

### Autonomous / Zero-Touch Networks

- **El Rajab, Yang & Shami (2024)** — "Zero-Touch Networks: Towards Next-Generation Network Automation," arXiv:2312.04159. Survey of ZSM framework, AutoML integration, and 5G+ self-management.[^10]
- **Nokia (2025)** — "Towards cognitive and fully autonomous 6G networks," White paper. Vision for agentic, intent-based, self-X networking at scale.[^8]

### Network Slicing

- **Alwakeel & Alnaim (2024)** — "Network Slicing in 6G: A Strategic Framework for IoT in Smart Cities," *Sensors*, 24(13), 4254. Advanced slicing framework with encryption and authentication for 6G IoT.[^13]
- **Zhuang et al. (2021)** — "AI-Native Network Slicing for 6G Networks," *IEEE Wireless Communications*. AI-driven slice management for SAGIN with RL-based resource reservation.[^14]

### Self-Healing WSN

- **Shyama, Pillai & Anpalagan (2022)** — "Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization," *Computer Networks*, 211, 109003. FTGSO for fault-free routing paths with 96.8% PDR.[^19]
- **Gayathri & Snigdha (2025)** — "Self-healing and energy-efficient cluster-based routing for sustainable WSNs," *Frontiers in Communications and Networks*, 6. SHEER protocol with trust-based CH selection and dynamic redistribution.[^22]
- **Hegde et al. (2025)** — "Autonomous Self-Healing UAV Swarms for Robust 6G Non-Terrestrial Networks," arXiv:2601.13418. RASHND architecture with SDR testbed and AERPAW UAV validation.[^23]

### Adaptive Routing

- **Aruna et al. (2025)** — "Adaptive ML-Driven Routing Framework for Secure and Energy-Efficient WSNs," *Int. J. Comp. Methods in Eng. & Mfg.*, 13(3). ML-driven path selection with anomaly detection for real-time security.[^28]
- **Multi-agent RL routing (2025)** — "Energy-Efficient Routing Algorithm for WSNs: A Multi-Agent Reinforcement Learning Approach," arXiv:2508.14679. Q-learning MARL framework with MERA and MST integration.[^29]
- **Abbas et al. (2024)** — "New Adaptive-Clustered Routing Protocol for Indoor Fire Emergencies Using Hybrid CNN-BiLSTM," *J. Intell. Sys. IoT*, 14(2). Context-aware routing for disaster scenarios.[^26]

### 6G Integration with WSN/IoT

- **IJRASET (2025)** — "Wireless Sensor Networks for IoT and 6G," comprehensive survey of WSN architecture, AI/ML edge integration, blockchain, and energy harvesting for 6G.[^30]
- **Zhang et al. (2025)** — "Semantic Edge Computing and Semantic Communications in 6G Networks: A Unifying Survey," *Computer Networks*, 111531. Unifying SEC and SemCom for edge intelligence in 6G.[^7]
- **6G Flagship (2026)** — "Building resilience into networks," 15th White Paper. Resilience as a 6G design objective integrating reliability, security, and adaptability.[^54]

### Sustainability / Carbon / Circular Economy

- **CHEDDAR (2025)** — "Towards Carbon-Neutrality for 6G Networks," White paper. Metrics (TCE, NCIe, REUR, RECOF) and carbon-aware decision engines for 6G.[^31]
- **Sustain-6G (2025)** — Deliverable D2.1: Sustainability baseline and lifecycle-oriented network planning for 6G.[^55]
- **GSMA (2024)** — "Circular Economy for Network Equipment Recommendations." CO₂ savings through equipment reuse, refurbishment, and lifecycle management.[^37]
- **Noor (2025)** — "Comprehensive Life Cycle Evaluation of Carbon Emission from ICT Equipment," Aalto University Master's Thesis. LCA finding up to 80% of ICT emissions from manufacturing.[^40]
- **NGMN (2021/2025)** — "Network Equipment Eco-Design and End-to-End Service Footprint." LCA methodology for network equipment environmental footprint.[^56]

### Disaster Monitoring

- **DOAJ (2025)** — "Disaster management-based IoT using WSN for flood monitoring," ZigBee-based flood detection with IoT integration.[^44]
- **Pognon et al. (2024)** — "Adaptive priority scheduling of IoT data for disaster monitoring in smart cities," *Polytechnique Montréal*. 31% improvement in urgent data latency over hierarchical WSN.[^42]
- **ScienceDirect (2025)** — "Advanced Network Slicing solutions for reliable Wi-Fi and 5G PPDR communications." Real-life network slicing for disaster response guaranteeing first-responder QoS.[^16]
- **AMAZING6G EU (2025)** — Public Safety use cases: B5G/6G PPDR network slices with MEC for wildfire/earthquake scenarios.[^18]

***

## Part 4: Research Gaps Justifying This Integrated Topic

### Gap 1: No Cross-Layer Data Reduction + Self-Healing Framework

Existing self-healing protocols (SHEER, FTGSO) operate independently of data reduction mechanisms. Data aggregation studies assume stable networks. No framework exists where self-healing decisions are informed by data reduction state (e.g., reconstruction quality degradation signals a topology problem) or where data reduction strategies adapt to self-healing reconfigurations. The SCR-DTRA work on self-healing data aggregation is the closest but remains limited to simple trust-based mechanisms without semantic or 6G-aware data reduction.[^49][^24][^22][^19]

### Gap 2: Absence of Sustainability-Aware WSN Design Beyond Operational Energy

Virtually all WSN sustainability literature focuses on operational energy efficiency—battery life, energy harvesting, sleep scheduling. Embodied carbon of sensor hardware, circular economy principles (node reuse, recyclability, modular design), and lifecycle-aware protocol design are absent from WSN research. This contrasts sharply with macro-network literature where embodied carbon and circular economy are active topics. Bridging this gap—designing WSN protocols that account for total lifecycle carbon including manufacturing and disposal—is a genuinely novel contribution.[^34][^35][^37][^56][^40]

### Gap 3: 6G-WSN Integration Lacks Holistic System Architecture

While 6G-WSN integration surveys exist, they remain at a high visionary level. Concrete system architectures that exploit specific 6G capabilities—network slicing for per-sensor-type QoS differentiation, semantic communication for disaster-specific data reduction, ISAC for combined sensing and communication, non-terrestrial network relay via UAVs—in an integrated WSN framework for disaster monitoring are absent. The RASHND work demonstrates UAV self-healing for 6G NTN but does not address WSN-level data management or sustainability.[^23][^30]

### Gap 4: Network Slicing Not Applied at WSN Granularity for Disaster Data

Network slicing for PPDR exists at the macro-network level (dedicated slices for voice, video, PLC). However, slicing at the WSN edge—where heterogeneous sensor data (seismic, hydrological, thermal, chemical) requires differentiated latency, reliability, and processing requirements—has not been explored. A disaster WSN generating both critical real-time alerts and bulk environmental logs needs slice-aware data reduction and routing strategies, which represents an open design space.[^16][^18]

### Gap 5: Carbon-Aware Decision-Making Not Integrated into Disaster Network Operations

Carbon-aware 6G networks with decision engines exist conceptually, but their application to disaster-deployed WSNs—where rapid deployment, potential node loss, and environmental damage create unique sustainability trade-offs—has not been studied. Disaster deployments face specific lifecycle questions: disposable vs. recoverable sensors, energy harvesting feasibility in disaster zones, and carbon cost of redundant deployments for resilience.[^31]

### Gap 6: No Unified Autonomous Framework Combining All Elements

Zero-touch and autonomous network concepts are mature for 5G/6G core, but translating cognitive autonomy to the resource-constrained WSN edge—where nodes must autonomously decide what data to reduce, how to heal routes, when to switch 6G slices, and how to minimize lifecycle carbon—represents a fundamentally different optimization problem requiring novel architectural and algorithmic contributions.[^9][^11][^10]

***

## Part 5: Suggested Refinements and Alternative Topic Phrasings

### Assessment of the Original Title

The original title—*"Autonomous Sustainable Data Reduction and Self-Healing Routing for 6G-Integrated Wireless Sensor Networks in Disaster Monitoring"*—covers significant ground. However, it could be sharpened to better signal the specific novel contributions and align with the language of top venues (IEEE JSAC, IEEE TWC, IEEE TGCN, IEEE IoT-J, Computer Networks).

### Recommended Refinements

**Option A – Emphasizing the carbon/lifecycle novelty (strongest differentiator):**
> *"Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for 6G-Integrated Disaster Sensor Networks: A Lifecycle-Sustainable Approach"*

This phrasing foregrounds the lifecycle/carbon dimension—the rarest element in current literature—while retaining all other components. "Carbon-aware" connects to the active 6G sustainability discourse.[^31]

**Option B – Emphasizing semantic communication and 6G-native design:**
> *"Semantic-Driven Data Reduction with Self-Healing Routing in 6G-Native WSNs for Resilient Disaster Monitoring"*

This positions the work within the emerging semantic communication paradigm and replaces "sustainable" (which can be vague) with a concrete technical mechanism.[^7]

**Option C – Emphasizing zero-touch and cross-layer integration:**
> *"Zero-Touch Cross-Layer Data Reduction and Self-Healing for 6G-Integrated Sustainable Disaster Sensor Networks"*

"Zero-touch" directly links to the ETSI ZSM standard and signals autonomous operation. "Cross-layer" highlights the integration novelty.[^9]

**Option D – Emphasizing network slicing differentiation:**
> *"Slice-Aware Sustainable Data Reduction and Self-Healing Routing for Heterogeneous 6G Disaster Sensor Networks"*

This highlights the novel application of slicing at the WSN edge level for differentiated disaster data.

### Strategic Recommendations for Maximizing Impact

- **Narrow the disaster domain** to one or two specific scenarios (e.g., wildfire + flood) for concrete evaluation rather than generic "disaster monitoring."
- **Define "sustainable" precisely** in the thesis scope: recommend including embodied carbon, lifecycle assessment, and energy harvesting—not just operational energy efficiency—to differentiate from hundreds of existing "energy-efficient WSN" papers.
- **Incorporate semantic communication** as the data reduction mechanism, as this is a high-impact 6G-native approach that subsumes and extends traditional compression/aggregation.[^6]
- **Target journals:** IEEE Transactions on Green Communications and Networking (TGCN), IEEE Internet of Things Journal, IEEE Journal on Selected Areas in Communications (JSAC—6G special issues), or Computer Networks for the networking systems perspective.
- **Build a testbed or simulation** combining ns-3/OMNeT++ for WSN-level simulation with 6G system-level simulators and lifecycle carbon calculators to provide concrete, reproducible results.
- **Consider digital twin integration** as an enabling architecture for the autonomous, self-healing, carbon-aware decision loop, which would further strengthen the novelty and align with active 6G research.[^46][^57]

***

## Conclusion

The proposed PhD topic occupies a genuinely novel intersection of well-studied individual components. The strongest novelty claims lie in three areas: (1) the integration of lifecycle sustainability (embodied carbon, circular economy) into WSN protocol design, which is virtually absent in current literature; (2) the cross-layer coupling of data reduction and self-healing routing as mutually informed subsystems rather than independent mechanisms; and (3) the application of 6G-native capabilities (network slicing, semantic communication, ISAC) at WSN edge granularity for disaster scenarios. Refining the title to foreground one of these specific contributions—while maintaining the integrated scope—will maximize the topic's clarity, impact, and positioning for top-tier publication venues.

---

## References

1. [Less is more: data reduction in wireless sensor networks](https://research.utwente.nl/en/publications/less-is-more-data-reduction-in-wireless-sensor-networks)

2. [Data Reduction Techniques in Wireless Sensor Network](https://www.rroij.com/open-access/data-reduction-techniques-in-wireless-sensornetwork-a-survey.pdf)

3. [Data transmission reduction techniques for improving ...](https://onlinelibrary.wiley.com/doi/abs/10.1002/ett.4674) - by K Jain · 2023 · Cited by 32 — Data transmission reduction techniques for improving network lifeti...

4. [Energy Conservation through Efficient Data Collection and Processing Techniques in Resource-Constrained Wireless Sensor Networks](https://morphpublishing.com/index.php/JCIMRD/article/view/2025-02-10) - This paper presents a framework for energy conservation in resource-constrained wireless sensor netw...

5. [Redefining IoT networks for improving energy and memory ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12297550/) - Wireless Sensor Networks (WSNs) have a wide range of applications across multiple platforms within t...

6. [A comprehensive review of AI-native 6G: integrating ...](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2025.1655410/full) - This review explores the evolving vision of sixth-generation (6G) networks as a paradigm shift from ...

7. [Semantic Edge Computing and Semantic Communications in 6G ...](https://arxiv.org/abs/2411.18199) - Semantic Edge Computing (SEC) and Semantic Communications (SemComs) have been proposed as viable app...

8. [[PDF] Towards cognitive and fully autonomous 6G networks - Nokia](https://www.nokia.com/asset/i/215139/) - 6G must move beyond fragmented, reactive automation to cognitive, agent-driven autonomy that enables...

9. [Zero-Touch Networks (ZTNs)](https://www.emergentmind.com/topics/zero-touch-networks-ztns) - Explore Zero-Touch Networks: fully autonomous architectures for next-gen 5G/6G, harnessing AI/ML for...

10. [Zero-Touch Networks: Towards Next-Generation Network Automation](https://ar5iv.labs.arxiv.org/html/2312.04159) - The Zero-touch network and Service Management (ZSM) framework represents an emerging paradigm in the...

11. [High-value scenarios for autonomous networks level 4](https://www.tmforum.org/catalysts/projects/C24.5.756/innovation-pioneer-project-highvalue-scenarios-for-autonomous-networks-level-4) - Showcasing high-value autonomous network Level 4 scenarios, unifying the vision across TM Forum memb...

12. [[PDF] AI-Native Integrated Sensing and Communications for Self - arXiv.org](https://www.arxiv.org/pdf/2601.02398.pdf) - This section reviews how machine learning and AI algorithms are enabling wireless networks to autono...

13. [Network Slicing in 6G: A Strategic Framework for IoT ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC11243923/) - The emergence of 6G communication technologies brings both opportunities and challenges for the Inte...

14. [AI-Native Network Slicing for 6G Networks](https://uwaterloo.ca/scholar/sites/ca.scholar/files/wzhuang/files/wen_wcm_nov21.pdf)

15. [Balancing resource utilization and slice dissatisfaction ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12217554/) - Next-generation networks must address challenges such as exponential user growth, escalating traffic...

16. [Advanced Network Slicing solutions for reliable Wi-Fi and 5G ...](https://www.sciencedirect.com/science/article/abs/pii/S0140366425001550) - In this paper, we deploy real-life Network Slicing mechanism for Wi-Fi and 5G networks, to guarantee...

17. [Demonstration of slicing for PPDR communications](https://fidal-he.eu/publications/conference-papers/demonstration-slicing-ppdr-communications)

18. [Public Safety Use cases](https://amazing6g.eu/use-cases/public-safety/)

19. [Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization](https://www.sciencedirect.com/science/article/pii/S1389128622003930) - A wireless sensor network (WSN) is used in area monitoring, surveillance, virtual reality, artificia...

20. [Application of Self-Healing in Wireless Sensor Network](https://ouci.dntb.gov.ua/en/works/9JnkDzV9/) - Wireless Sensor Networks (WSNs) are gaining popularity in many monitoring and event detection areas....

21. [217](https://www.irma-international.org/viewtitle/149360/?isxn=9781466697928)

22. [Self-healing and energy-efficient cluster-based routing for ... - Frontiers](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2025.1602928/full) - The self-healing mechanism concentrates on network stability by detecting and replacing the failing ...

23. [Autonomous Self-Healing UAV Swarms for Robust 6G Non ...](https://arxiv.org/html/2601.13418v1)

24. [Self-Healing Approach for Fault-Tolerant Data Aggregation in WSN](https://ijrpr.com/uploads/V6ISSUE2/IJRPR38523.pdf)

25. [Adaptive Location-based Routing Protocols for Dynamic Wireless Sensor Networks in Urban Cyber-physical Systems](https://journaljerr.com/index.php/JERR/article/view/1220)

26. [New Adaptive-Clustered Routing Protocol for Indoor Fire Emergencies Using Hybrid CNN-BiLSTM Model: Development and Validation](https://www.americaspg.com/articleinfo/18/show/3261) - american scientific publishing group

27. [Optimizing Routing Efficiency in 5G/6G WSNs for ...](https://www.jetir.org/papers/JETIR2506208.pdf)

28. [Adaptive machine learning-driven routing framework for ...](https://www.acadlore.com/article/IJCMEM/2025_13_3/ijcmem130301)

29. [Energy-Efficient Routing Algorithm for Wireless Sensor Networks: A Multi-Agent Reinforcement Learning Approach](https://www.arxiv.org/abs/2508.14679) - Efficient energy management is essential in Wireless Sensor Networks (WSNs) to extend network lifeti...

30. [A Wireless Sensor Networks for IoT and 6G - IJRASET](https://www.ijraset.com/research-paper/wireless-sensor-networks-for-iot-and-6g) - Wireless Sensor Networks (WSNs) have emerged as a core technology for making intelligent environment...

31. [White Paper | Towards Carbon-Neutrality for 6G Networks](https://cheddarhub.org/wp-content/uploads/sites/168/White_Paper__Final_.pdf)

32. [Semantic Edge Computing and Semantic Communications in 6G ...](https://arxiv.org/html/2411.18199v3) - Semantic Edge Computing (SEC) and Semantic Communications (SemComs) have been proposed as viable app...

33. [Generation Wireless Systems through Energy Harvesting](https://jcbi.org/index.php/Main/article/download/642/566/1845)

34. [Advances in energy harvesting for sustainable wireless sensor ...](https://repository.up.ac.za/items/39de5603-9da0-42d6-a629-0b26b1278555) - Energy harvesting wireless sensor networks (EH-WSNs) appear as the fundamental backbone of research ...

35. [Efficient Green Protocols for Sustainable Wireless Sensor Networks](https://scholars.duke.edu/publication/1454928) - Scholars@Duke

36. [The environmental sustainability of communication networks](https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/02/the-environmental-sustainability-of-communication-networks_66fe3a2a/d1cb2210-en.pdf)

37. [42-50 Circular Economy for network equipment RECOMMENDATIONS.indd](https://www.gsma.com/solutions-and-impact/industry-services/wp-content/uploads/2024/02/Strategy-Paper-for-Circular-Economy-Network-Equipment-1.pdf)

38. [Ericsson is exploring AI focused on 6G and sustainability](https://www.ericsson.com/en/blog/2025/3/ai-driven-sustainability) - Evaluating AI's sustainability involves conducting a comprehensive Life Cycle Assessment (LCA), whic...

39. [[PDF] 6G Energy Efficiency and Sustainability](https://www.iis.fraunhofer.de/content/dam/iis/en/doc/lv/Whitepaper6GSustainability.pdf)

40. [[PDF] Comprehensive Life Cycle Evaluation of Carbon Emission from ICT ...](https://aaltodoc.aalto.fi/server/api/core/bitstreams/12ebab18-4591-4499-9e54-27594d99373f/content)

41. [[PDF] Comprehensive Life Cycle Evaluation of Carbon Emission from ICT ...](https://aaltodoc.aalto.fi/bitstreams/12ebab18-4591-4499-9e54-27594d99373f/download) - Researchers can use life cycle assessment (LCA) to measure the environmental impact of ICT equipment...

42. [[PDF] Adaptive priority scheduling of Internet of Things data for disaster ...](https://publications.polymtl.ca/58577/1/2024_Pognon_Adaptive_Priority_Scheduling_Internet_Things.pdf) - 1) We design an adaptive scheduling method for IoT data in smart cities aimed at reducing transmissi...

43. [a comprehensive review of IoT-enabled WSN path planning for ...](https://dl.acm.org/doi/abs/10.1007/s10586-025-05211-5) - This paper reviews the applications of IoT-enabled WSNs in disaster management, emphasizing the crit...

44. [Disaster management-based internet of things using ...](https://doaj.org/article/07fefa00ddd2431ab45030b73a1bf92f) - Wireless Sensor Networks (WSNs) have become essential in the monitoring and managing environmental d...

45. [International Journal for Multidisciplinary Research (IJFMR)](https://ijfmr.com/papers/2024/6/31605.pdf)

46. [Transforming resilience with predictive digital twin technologies](https://journalwjbphs.com/sites/default/files/fulltext_pdf/WJBPHS-2025-0850.pdf) - Abstract. This research examines the role of digital twin technology in enhancing disaster preparedn...

47. [[PDF] Emergency Response Automation (ERA) as a Safety-Critical System](https://egusphere.copernicus.org/preprints/2026/egusphere-2025-5776/egusphere-2025-5776.pdf) - ERA employs a 6G–blockchain communication layer as a task-scheduling platform to enable cross-organi...

48. [© 2024 JETIR February 2024, Volume 11, Issue 2                                                                www.jetir.org (ISSN-2349-5162)](https://www.jetir.org/papers/JETIR2402409.pdf)

49. [This is a title](https://publications.eai.eu/index.php/sis/article/download/6924/3551/20195)

50. [An Energy-Efficient Scheduling and Routing Protocol Based on Q ...](https://iprjb.org/journals/AJCET/article/view/3541) - Purpose: This article introduces an energy-efficient routing protocol for wireless sensor networks (...

51. [[PDF] Advances in Energy Harvesting for Sustainable Wireless Sensor ...](https://repository.up.ac.za/server/api/core/bitstreams/4fb13bc4-1f14-4013-a6f0-129f991a846e/content)

52. [IEEE COMMUNICATIONS MAGAZINE, VOL. XX, NO. XX, MAY 2024](http://arxiv.org/pdf/2408.13298.pdf)

53. [Rethinking digital twin: Introducing digital risk twin for disaster risk management](https://www.nature.com/articles/s44304-025-00135-x) - The digital risk twin (DRT) adapts digital twin (DT) for disaster risk management (DRM) by integrati...

54. [Building resilience into networks - 6G Flagship's 15th White Paper](https://www.6gflagship.com/news/building-resilience-into-networks-white-paper/) - It starts quietly, the way crises often do. A storm knocks out power across a city. A cyberattack ri...

55. [[PDF] Deliverable D2.1 Sustainability baseline, Use Cases ... - sustain-6g](https://sustain-6g.eu/wp-content/uploads/2025/08/sustain-6g_d2.1_sustainability_baseline_use_cases_baseline_requirements-_v1.0.pdf) - Lifecycle-oriented network planning is essential, synchronising equipment lifecycles with decarbonis...

56. [Green Future Networks: Network Equipment Eco-Design and End to End Service Footprint - NGMN](https://www.ngmn.org/publications/network-equipment-eco-design-and-end-to-end-service-footprint.html) - NGMN White Paper on Network Equipment Eco-Design and End to End Service Footprint. Second in a serie...

57. [Network Resiliency and Fault Tolerance through Digital Twins and ...](https://ajpojournals.org/journals/ajdikm/article/view/2682) - Digital twins enable real-time monitoring, predictive analytics, and scenario simulation by creating...


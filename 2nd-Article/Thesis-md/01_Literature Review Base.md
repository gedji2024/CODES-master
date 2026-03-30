# Literature Review: Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for 6G-Integrated Disaster Sensor Networks — A Lifecycle-Sustainable Approach

## Overview

This structured literature review synthesizes the current state of research across six interconnected themes that form the foundation of carbon-aware, lifecycle-sustainable 6G disaster sensor networks. Each theme presents key papers with extracted objectives, methodologies, results, and limitations, followed by an identification of research gaps. The review covers: (1) data reduction in WSNs, (2) autonomous WSN operation, (3) self-healing and adaptive routing, (4) 6G integration with IoT, (5) sustainability and carbon-awareness in network design, and (6) disaster monitoring applications.

***

## 2.1 Data Reduction in Wireless Sensor Networks

Data reduction is essential in WSNs because sensor nodes are energy-constrained and transmitting raw data is the dominant energy cost. Techniques span in-network processing, data compression, prediction-based suppression, and compressive sensing.[^1]

### 2.1.1 Key Studies

**Dias, Bellalta & Oechsner (2016) — "A Survey About Prediction-Based Data Reduction in WSNs"**
- **Objective:** Categorize and analyze prediction-based data reduction mechanisms for WSNs.[^2]
- **Methodology:** Systematic survey of dual prediction schemes (DPS), model-driven approaches, and forecasting algorithms (LMS, ARIMA, Kalman filters).[^2]
- **Key Results:** Prediction-based approaches can reduce transmissions by up to 98% in high-workload sensor nodes while maintaining measurement quality.[^3]
- **Limitations:** Most models assume stationary data distributions; performance degrades in non-stationary disaster environments. Audio-video data not well supported.[^1]

**Morales, Rangel de Sousa, Brusamarello & Fernandes (2021) — "Evaluation of Deep Learning Methods in a Dual Prediction Scheme to Reduce Transmission Data in a WSN"**
- **Objective:** Compare deep learning architectures (LSTM, GRU, CNN) for dual prediction-based transmission reduction.[^4]
- **Methodology:** Deployed deep learning models at both sensor and sink sides, evaluated on real environmental sensor data.[^4]
- **Key Results:** Deep learning models outperformed traditional forecasting (LMS, ARIMA) in prediction accuracy, further reducing required transmissions.
- **Limitations:** Computational overhead of deep learning models may be prohibitive for resource-constrained sensor nodes without edge offloading.[^4]

**IJISAE (2023) — "Data Reduction Techniques in WSN with IoT"**
- **Objective:** Address energy consumption and redundant data storage in IoT-connected WSNs.[^5]
- **Methodology:** Proposed Two-Tier Data Reduction (TTDR) applied at both sensor nodes and gateways, validated using OMNeT++ with real sensory data.[^5]
- **Key Results:** TTDR achieved significant reductions in data transfer volume and energy consumption across both network tiers.[^5]
- **Limitations:** Only evaluated on environmental monitoring data; scalability to disaster scenarios with bursty, heterogeneous data was not assessed.[^5]

**Xu, Ansari & Khokhar (2012) — "Power-Efficient Hierarchical Data Aggregation Using Compressive Sensing in WSN"**
- **Objective:** Combine multi-resolution hierarchical structures with compressive sensing (CS) for energy-efficient data aggregation.[^6]
- **Methodology:** Variable compression thresholds across the aggregation hierarchy; simulated on SIDnet-SWANS platform.[^6]
- **Key Results:** Energy savings of 37%–77% depending on node position in the hierarchy.[^6]
- **Limitations:** Assumed fixed network topology; did not address dynamic scenarios where nodes fail or are destroyed.[^6]

**Nature Scientific Reports (2025) — "Compressive Sensing Techniques Based on Secure Data Aggregation"**
- **Objective:** Combine CS with elliptic curve cryptography (ECC) for simultaneous data compression and encryption.[^7]
- **Methodology:** Proposed SP, AMP, and SBI algorithms integrated with ECDH key exchange; tested across varying network sizes.[^7]
- **Key Results:** The CS+ECC approach significantly extended network lifetime while providing data security. SP, AMP, and SBI algorithms achieved the lowest energy dissipation.[^7]
- **Limitations:** Added cryptographic overhead increases per-node processing time; trade-offs between security level and energy savings not fully characterized.[^7]

**Pioli, Dorneles, de Macedo & Dantas (2022) — "An Overview of Data Reduction Solutions at the Edge of IoT Systems"**
- **Objective:** Systematically map data reduction techniques performed exclusively at the edge layer.[^8]
- **Methodology:** Systematic literature mapping of 35 papers from 853 candidates; analyzed techniques, hardware, and data types.[^8]
- **Key Results:** Filtering, aggregation, and compression at the edge are the most commonly employed strategies. Edge-based reduction reduces both bandwidth and cloud storage costs.[^8]
- **Limitations:** Most studies did not consider real-time disaster workloads or heterogeneous multi-modal sensor data at the edge.[^8]

### 2.1.2 Gaps and Limitations

- Most data reduction techniques assume **stationary or slowly varying data**, which poorly matches the rapid, unpredictable changes seen in disaster environments (seismic events, flash floods).[^3][^1]
- **Carbon-awareness** is absent from all surveyed data reduction schemes — no existing work adjusts compression or aggregation decisions based on the carbon intensity of the energy source.
- There is limited integration of **data reduction with self-healing routing**, meaning when nodes fail during disasters, the data reduction pipeline typically breaks without graceful degradation.[^6]
- Deep learning-based approaches show promise but face **deployment barriers on ultra-low-power MCUs** without edge offloading support.[^9][^4]

***

## 2.2 Autonomous Wireless Sensor Networks

Autonomic computing principles — self-configuration, self-optimization, self-healing, and self-protection — enable WSNs to operate without human intervention in remote or hazardous environments.[^10]

### 2.2.1 Key Studies

**Portocarrero, Delicato, Pires et al. (2014) — "Autonomic Wireless Sensor Networks: A Systematic Literature Review"**
- **Objective:** Survey WSN middleware systems that implement autonomic computing (AC) self-* properties.[^10]
- **Methodology:** Systematic literature review identifying which AC development approaches are used for WSN middleware.[^10]
- **Key Results:** The most commonly addressed properties are self-configuration and self-optimization. Fewer studies address self-healing and self-protection. Middleware-based approaches provide the abstraction layer needed for autonomic behavior.[^10]
- **Limitations:** Most studies address self-* properties in isolation; few integrate all four autonomic properties into a unified framework. Real-world validation in disaster scenarios was absent.[^10]

**Nguyen, Shieh, Horng & Dao (2014) — "A Genetic Algorithm with Self-Configuration Chromosome for the Optimization of WSNs"**
- **Objective:** Enable self-organization in WSNs through GA-based cluster formation to minimize communication distances and extend network lifetime.[^11]
- **Methodology:** Genetic algorithm with self-configuration chromosomes for cluster head selection and optimized network deployment.[^11]
- **Key Results:** The approach outperformed baseline protocols in solution quality and convergence speed for cluster optimization.[^11]
- **Limitations:** Assumes static deployment; does not handle dynamic node arrival/departure or disaster-induced topology disruptions.[^11]

**Nature Scientific Reports (2025) — "Self-Organizing Complex Networks with AI-Driven Adaptive Nodes"**
- **Objective:** Develop an AI-enhanced self-organizing network model where each node autonomously adjusts connectivity for robustness and energy efficiency.[^12]
- **Methodology:** Each node uses AI-based decision-making to dynamically adjust transmission power and establish connections based on local topology and energy constraints.[^12]
- **Key Results:** The model demonstrated improved network robustness, resilience to node failures, and efficient energy usage in large-scale distributed simulations.[^12]
- **Limitations:** Computational demands of per-node AI inference may exceed the capabilities of low-power sensor hardware. No carbon or lifecycle sustainability metrics considered.[^12]

**Sensor Networks Research Group (2024) — "Sensor Autonomy: Enabling Self-Configuring and Self-Healing Sensor Networks"**
- **Objective:** Provide a conceptual overview of how machine learning and AI empower sensor autonomy for self-configuration and self-healing.[^13]
- **Methodology:** Review of architectures incorporating ML-based self-organization, power adjustment, and fault recovery.[^13]
- **Key Results:** Autonomous sensors that adjust transmission power, communication protocols, and data processing algorithms achieve higher network efficiency and robustness.[^13]
- **Limitations:** Conceptual review; lacks empirical benchmarks or simulation results specific to disaster environments.[^13]

### 2.2.2 Gaps and Limitations

- Existing autonomic WSN frameworks address self-* properties **in isolation** (e.g., self-configuration OR self-healing), not as an integrated lifecycle management system.[^10]
- No study ties autonomous WSN behavior to **carbon-awareness** — the self-optimization objective is always energy or latency, never carbon footprint.
- Validation is predominantly through **simulation with idealized conditions**; real-world deployments in harsh disaster environments remain rare.[^13][^11]

***

## 2.3 Self-Healing and Adaptive Routing in WSNs

Self-healing routing ensures continuous data delivery despite node failures, which is critical in disaster settings where physical damage to sensors is expected.[^14][^15]

### 2.3.1 Key Studies

**Shyama, Pillai & Anpalagan (2022) — "Self-Healing and Optimal Fault-Tolerant Routing in WSNs Using Genetical Swarm Optimization"**
- **Objective:** Improve the self-healing capacity and fault tolerance of WSNs using a hybrid metaheuristic.[^14]
- **Methodology:** Genetical Swarm Optimization (GSO), combining GA and PSO, for cluster head selection (based on residual energy, coverage, communication cost) and fault-free routing path identification.[^14]
- **Key Results:** Achieved 96.8% PDR, 0.19 J energy consumption, 3.2% packet loss ratio, and 30 ms E2E delay — outperforming existing optimization-based routing protocols.[^14]
- **Limitations:** Evaluated in simulated single-fault scenarios; performance under simultaneous large-scale failures (as in earthquakes) was not tested.[^14]

**Gayathri & Snigdha (2025) — "Self-Healing and Energy-Efficient Cluster-Based Routing (SHEER) for Sustainable WSNs"**
- **Objective:** Develop a clustering mechanism with integrated self-healing for CH selection considering energy, distance, and trust metrics.[^16]
- **Methodology:** SHEER protocol with dynamic CH/CM redistribution upon node failure; simulated in Cooja software with 100–500 nodes.[^16]
- **Key Results:** 98% PDR, 2% PLR, reduced energy consumption, and stable cluster maintenance even under node failures.[^16]
- **Limitations:** While framed as "sustainable," sustainability refers only to network lifetime extension — no environmental lifecycle or carbon metrics are included.[^16]

**Abba & Lee (2015) — "An Autonomous Self-Aware and Adaptive Fault-Tolerant Routing Technique (ASAART) for WSNs"**
- **Objective:** Address limitations of self-healing routing (SHR) and self-selective routing (SSR) by integrating autonomic self-awareness and adaptive fault detection.[^17]
- **Methodology:** Combined continuous and slotted prioritized back-off delays with multiple random functions for route formation and repair under transient and permanent failures.[^17]
- **Key Results:** ASAART outperformed SHR and SSR across five scenarios with improved routing convergence and reliable route repair.[^17]
- **Limitations:** Focused on single-path recovery; did not explore multi-path or redundancy-based strategies for large-area failures.[^17]

**Lee & Jung (2010) — "Speedy Routing Recovery Protocol (ARF) for Large Failure Tolerance in WSNs"**
- **Objective:** Enable fast routing recovery after large-area node failures in hazardous environments.[^18]
- **Methodology:** ARF detects failures via packet loss counting and decreases routing intervals to rapidly propagate failure notifications to neighbors.[^18]
- **Key Results:** ARF recovered from large-area failures more quickly and with fewer packets and less energy than previous protocols.[^18]
- **Limitations:** Protocol overhead increases with network density; not tested with realistic disaster damage patterns.[^18]

**Soltani, Eskandarpour, Ahmadizad & Soleimani (2025) — "Energy-Efficient Routing Algorithm for WSNs: A Multi-Agent Reinforcement Learning Approach"**
- **Objective:** Develop adaptive multi-hop routing using multi-agent RL (Q-learning) for dynamic energy-aware path selection.[^19]
- **Methodology:** Each sensor node modeled as an autonomous agent observing residual energy, distance to sink, hop count, and hotspot proximity. Reward function incentivizes balanced load distribution and hotspot avoidance.[^19]
- **Key Results:** Significantly improved node survival rate, reduced SoC variance, and enhanced network resilience compared to classical graph-based methods (MERA, MST).[^19]
- **Limitations:** RL training convergence time may be impractical in rapidly evolving disaster scenarios. Cloud-based training offloading assumes connectivity that may not exist post-disaster.[^19]

**Zhang & Liu (2025) — "Improving WSN Functionality Through Reinforcement Learning and Metaheuristic-Based Energy-Efficient Systems"**
- **Objective:** Combine Harris Hawks Optimization for clustering with RL-trained fuzzy logic for cluster head selection.[^20]
- **Methodology:** Fuzzy rules optimized via Wild Horse Optimization considering maximum energy and minimum neighbor distance.[^20]
- **Key Results:** 29% increase in network lifetime and 46% increase in data volume delivered to the base station.[^20]
- **Limitations:** Multi-step optimization pipeline introduces computational complexity unsuitable for resource-constrained disaster deployments.[^20]

### 2.3.2 Gaps and Limitations

- Most self-healing protocols are evaluated under **controlled single-fault or random-fault models** — not the correlated, spatially clustered failures characteristic of natural disasters (earthquakes destroying entire zones).[^18][^14]
- **No existing self-healing protocol incorporates carbon-awareness** — recovery path selection is based on energy/latency but never on the carbon intensity of the energy powering the nodes.
- Reinforcement learning approaches assume **training data and convergence time** that may not be available post-disaster when networks must self-heal immediately.[^19]
- The term "sustainable" in WSN routing literature uniformly refers to **network lifetime**, not environmental sustainability or lifecycle carbon.[^16]

***

## 2.4 6G Integration with IoT and Wireless Sensor Networks

6G networks are expected to deliver terabit-per-second data rates, sub-millisecond latency, and native support for massive IoT — creating new possibilities for WSN integration in mission-critical applications.[^21][^22]

### 2.4.1 Key Studies

**IJRASET (2025) — "Wireless Sensor Networks for IoT and 6G"**
- **Objective:** Survey the state-of-the-art in WSN innovation for IoT and 6G, covering architecture, energy harvesting, and AI integration.[^21]
- **Methodology:** Comprehensive literature review examining energy-efficient routing (LEACH, AODV, HEED), AI/ML for smart aggregation, and 6G integration challenges.[^21]
- **Key Results:** AI-based integration with 6G is identified as the primary driver for future WSN performance. Reinforcement learning for adaptive routing and edge computing for data processing are highlighted as key enablers.[^21]
- **Limitations:** The survey identifies gaps but does not propose concrete solutions. No treatment of disaster-specific WSN requirements or carbon-aware operation.[^21]

**Alwakeel & Alnaim (2024) — "Network Slicing in 6G: A Strategic Framework for IoT in Smart Cities"**
- **Objective:** Develop an advanced network slicing framework for 6G smart city IoT deployments.[^23]
- **Methodology:** Comprehensive methodology covering requirement analysis, metric formulation, constraint specification, mathematical modeling, and performance evaluation.[^23]
- **Key Results:** Low RTT, minimal packet loss, increased availability, enhanced throughput, and effective scaling across multiple simultaneous connections. 256-bit encryption for security.[^23]
- **Limitations:** Focused on smart city scenarios; disaster environments with destroyed infrastructure and unpredictable traffic patterns were not addressed.[^23]

**Sasan & Khorsandi (2025) — "Balancing Resource Utilization and Slice Dissatisfaction Through Dynamic Soft Slicing for 6G"**
- **Objective:** Address the trade-off between resource utilization and QoS guarantees in 6G network slicing.[^24]
- **Methodology:** MILP formulation for maximizing utilization while minimizing slice dissatisfaction; HRASS heuristic algorithm for near-optimal performance.[^24]
- **Key Results:** Soft slicing achieved better resource utilization than hard slicing while maintaining user-level QoS guarantees for hybrid 6G use cases.[^24]
- **Limitations:** NP-hard optimization assumes centralized orchestration; real-time adaptation in emergency/disaster scenarios with infrastructure loss not explored.[^24]

**6G Terahertz Communication — Multiple Sources (2024–2025)**
- **Objective:** Explore THz communication (100 GHz–10 THz) as a key 6G enabler for ultra-high data rates.[^25][^22]
- **Key Findings:** THz bands offer enormous bandwidth for Tbps wireless links; sub-THz (90–300 GHz) is the first 6G deployment target. Intelligent Reflecting Surfaces (IRS) and Massive MIMO are being integrated to mitigate path loss. However, THz communication faces high path loss, limited range, and extreme power demands.[^22][^26][^27][^25]
- **Limitations:** THz communication is inherently short-range and line-of-sight dependent, making it poorly suited for outdoor disaster sensor networks where environmental obstruction is common.[^26]

**PMC (2022) — "Future Wireless Communication Technology Towards 6G IoT"**
- **Objective:** Propose an IoT-based monitoring system architecture aligned with 6G vision.[^28]
- **Methodology:** Prototyped a real-time location monitoring system using BLE as a proof of concept for 6G IoT sensing.[^28]
- **Key Results:** Demonstrated feasibility of low-power IoT integration for 6G-ready applications.[^28]
- **Limitations:** BLE prototype is far from 6G specifications; primarily a conceptual alignment rather than true 6G implementation.[^28]

### 2.4.2 Gaps and Limitations

- 6G research focuses overwhelmingly on **smart cities, XR, and autonomous vehicles** — very few studies address disaster response as a primary use case.[^23][^24]
- **Network slicing for disaster scenarios** is under-explored: no framework dynamically reconfigures slices when infrastructure is destroyed and must fall back to ad-hoc mesh WSN operation.
- The **energy and carbon cost of 6G infrastructure** (dense small cells, IRS, massive MIMO arrays) is rarely analyzed, despite 6G's sustainability goals.[^22][^21]
- Integration between 6G backhaul and resource-constrained **WSN sensor tiers** remains architecturally under-specified — most work assumes homogeneous 6G endpoints, not heterogeneous sensor-to-6G hierarchies.

***

## 2.5 Sustainability, Energy Efficiency, and Carbon-Awareness in Network Design

Sustainability in network design encompasses operational energy efficiency, embodied carbon from manufacturing, lifecycle assessment, circular economy principles, and carbon-aware scheduling.[^29][^30]

### 2.5.1 Key Studies

**Ruiz et al. (2022) — "Life Cycle Inventory and Carbon Footprint Assessment of Wireless ICT Networks"**
- **Objective:** Quantify the carbon footprint of 4G LTE networks across the full lifecycle, distinguishing embodied from operational emissions.[^29]
- **Methodology:** Life cycle assessment (LCA) covering extraction, manufacturing, transport, operation, and end-of-life for user devices, eNodeB, EPC, and data centers across six demographic scenarios.[^29]
- **Key Results:** Embodied emissions constitute a significant and often underestimated portion of total network carbon. Urban deployments have lower per-user carbon than rural/remote deployments due to infrastructure sharing.[^29]
- **Limitations:** Focused on 4G LTE; did not extend to 5G/6G or WSN-specific deployments. Sensor node embodied carbon was not assessed.[^29]

**Wagih (2024) — "Environmental Life-Cycle Assessment (LCA) of Wireless Sensors"**
- **Objective:** Assess the environmental impact of wireless sensor hardware across its lifecycle.[^31]
- **Methodology:** LCA of active microwave sensor systems analyzing embodied carbon contributions of ICs, PCBs, and packaging.[^31]
- **Key Results:** Over 80% of embodied carbon comes from integrated circuits (ICs). Opting for simpler IC architectures can substantially reduce the manufacturing carbon footprint.[^31]
- **Limitations:** Focused on individual sensor hardware; did not model the carbon footprint of full-scale sensor network deployments or operational carbon from data transmission.[^31]

**Piastou (2026) — "Green Software Development Using Carbon-Aware Scheduling Techniques"**
- **Objective:** Systematize carbon-aware scheduling approaches and energy efficiency metrics throughout the software development lifecycle.[^30]
- **Methodology:** Analysis of peer-reviewed articles (2020–2025) identifying four strategies: temporal task shifting, geographic load migration, electricity price consideration, and dynamic resource scaling.[^30]
- **Key Results:** Carbon-aware scheduling can reduce application carbon footprint by 30–70% with moderate latency impact. Ignoring early SDLC phases underestimates the total carbon footprint.[^30]
- **Limitations:** Trade-offs between emission reduction and service quality are acknowledged but not fully resolved. Metric standardization and carbon-intensity forecasting accuracy remain open challenges.[^30]

**Carbon-Aware HPC Scheduling (2025)**
- **Objective:** Integrate carbon-intensity forecasting with multi-objective optimization for HPC job scheduling.[^32]
- **Methodology:** Dynamic scheduling aligned with real-time grid carbon intensity, combined with workload prediction and renewable energy availability.[^32]
- **Key Results:** 25.7% energy reduction and 40.5% carbon emission reduction compared to traditional scheduling methods.[^32]
- **Limitations:** Assumes access to real-time grid carbon data and predictable workload patterns — neither is guaranteed in disaster-deployed edge/sensor networks.[^32]

**Nature Scientific Reports (2025) — "Energy-Aware Adaptive Virtualization and Migration (EAVM) Protocol for Green IoT WSNs"**
- **Objective:** Address energy and sustainability challenges in large-scale Green IoT WSNs through adaptive virtualization.[^33]
- **Methodology:** Federated Deep Reinforcement Learning (FDRL) combined with hybrid solar–RF energy harvesting for dynamic virtual resource allocation and migration.[^33]
- **Key Results:** EAVM achieved enhanced energy efficiency, scalability, and sustainability relative to state-of-the-art Green IoT techniques.[^33]
- **Limitations:** FDRL requires significant computational resources for training; applicability to ultra-constrained disaster sensor nodes is questionable.[^33]

**Energy Harvesting in Self-Sustainable IoT — ScienceDirect (2023)**
- **Objective:** Bridge the gap between IoT applications and self-sustainable IoT system design through a cross-layer architecture.[^34]
- **Methodology:** Comprehensive survey of energy harvesting sources (solar, thermal, RF, kinetic), storage interfaces, and energy-saving methods across IoT layers.[^34]
- **Key Results:** Cross-layer EH architecture design can extend IoT device operational lifetimes. Emerging storage technologies (supercapacitors, thin-film batteries) enable continuous operation.[^34]
- **Limitations:** EH power output is environment-dependent and intermittent. Disaster environments may damage or occlude EH elements (solar panels covered by debris).[^34]

**Edge Computing and Sustainability (2026)**
- **Objective:** Examine how edge computing reduces carbon footprints by processing data locally instead of transmitting to centralized data centers.[^35]
- **Key Results:** Local processing reduces energy consumption, enables renewable energy integration at edge sites, and supports predictive maintenance for reduced downtime.[^35]
- **Limitations:** Edge devices still have embodied carbon costs; the sustainability benefit depends on the local energy mix and device lifecycle management.[^35]

### 2.5.2 Gaps and Limitations

- **Carbon-aware computing has not been applied to WSN/IoT sensor networks** — all existing work targets cloud data centers or HPC clusters, not distributed, resource-constrained sensor deployments.[^30][^32]
- **Embodied carbon of sensor nodes** is studied only at the individual component level; no end-to-end lifecycle carbon model exists for a full disaster sensor network (from manufacturing through deployment, operation, maintenance, and end-of-life).[^31]
- **Circular economy principles** (modular design, repairability, material recovery) are discussed for consumer electronics but have not been applied to sensor node hardware design for WSNs.[^36][^37]
- The concept of **lifecycle sustainability** — integrating operational carbon, embodied carbon, and end-of-life disposal into a single optimization framework — is entirely absent from the WSN literature.

***

## 2.6 Disaster Monitoring Applications Using WSNs

WSNs provide real-time environmental data critical for disaster early warning, enabling continuous monitoring of parameters such as water levels, seismic activity, soil moisture, and gas concentrations.[^38][^39]

### 2.6.1 Key Studies

**Benkhelifa, Nouali-Taboudjemat & Moussaoui — "Disaster Management Projects Using Wireless Sensor Networks: An Overview"**
- **Objective:** Survey recent WSN projects for disaster management and emergency response.[^39]
- **Methodology:** Comprehensive review of WSN applications including air pollution monitoring, forest fire detection, landslide detection, water level monitoring, and earthquake vibration detection.[^39]
- **Key Results:** WSNs offer a cost-effective alternative to traditional ad-hoc networks when infrastructure collapses. Multi-parameter monitoring (temperature, humidity, vibration, gas) improves detection accuracy.[^39]
- **Limitations:** Most projects are pilot-scale; large-scale, long-term disaster deployments face sustainability, maintenance, and reliability challenges that are inadequately addressed.[^39]

**IJFMR (2024) — "Wireless Sensor Network for Disaster Management"**
- **Objective:** Develop an integrated WSN system for multi-disaster monitoring (floods, earthquakes, weather, gas hazards).[^38]
- **Methodology:** Deployed water-level sensors, accelerometers, temperature/humidity sensors, and gas sensors transmitting to a central monitoring station.[^38]
- **Key Results:** Flood monitoring sensors accurately identified rising water levels; accelerometers captured seismic activity; the system generated real-time alerts for all monitored hazards.[^38]
- **Limitations:** Minor data transmission issues in high-interference areas; the system did not incorporate data reduction or energy-efficient routing for long-term operation.[^38]

**DOAJ (2025) — "Disaster Management-Based Internet of Things Using WSNs" (Flood Monitoring)**
- **Objective:** Develop a flood monitoring system using WSN with ZigBee and IoT integration for dam water-level monitoring.[^40]
- **Methodology:** Water-level sensors in dam basements using ZigBee for low-power transmission to a base station, with IoT-enabled mobile alerts.[^40]
- **Key Results:** The system accurately detected real-time water level variations. ZigBee provided enhanced energy efficiency, scalability, and transmission range compared to alternatives.[^40]
- **Limitations:** Single-hazard (flood only) system; no multi-hazard integration. No self-healing capability if sensor nodes are destroyed by the flood being monitored.[^40]

**Amrita University — "Real-Time Landslide Warning Systems"**
- **Objective:** Deploy a multi-level WSN for real-time landslide detection and early warning.[^41]
- **Methodology:** Hierarchical two-layer WSN with lower-layer low-cost sensors (pore pressure, moisture, strain, geophones, tilt meters, rain gauges) and upper-layer sophisticated relay nodes.[^41]
- **Key Results:** Successfully issued real-time alerts before impending landslides, facilitating evacuation. The hierarchical architecture allowed locally reliable decisions at the lower layer.[^41]
- **Limitations:** The fixed hierarchical architecture lacks self-healing; if upper-layer relay nodes are destroyed by the landslide, the entire sub-network is disconnected.[^41]

**IJIRT (2025) — "Smart Disaster Detection and Evacuation Alert System Using WSN and IoT"**
- **Objective:** Develop an intelligent system for real-time landslide detection with automated alerts.[^42]
- **Methodology:** Soil moisture, rainfall, and ground vibration sensors with IoT notifications and buzzer alerts when thresholds are exceeded.[^42]
- **Key Results:** Real-time monitoring and early warnings enabled rapid response; authorities could access data remotely for coordinated decision-making.[^42]
- **Limitations:** Threshold-based alerting is rigid; no adaptive learning or carbon-efficient operation was incorporated.[^42]

**ScienceDaily (2011) — "Greener Disaster Alerts: Low-Energy WSNs Warn of Hurricanes, Earthquakes"**
- **Objective:** Develop energy-efficient mesh WSN software for disaster monitoring that reduces energy consumption.[^43]
- **Methodology:** Mesh network of wireless sensors with periodic reporting to central site, optimized for reduced energy demand.[^43]
- **Key Results:** Achieved reduced energy requirements compared to conventional WSNs while maintaining monitoring fidelity for hurricane and seismic events.[^43]
- **Limitations:** "Green" refers solely to energy efficiency, not to lifecycle carbon footprint or material sustainability.[^43]

**Self-Healing Emergency Networks for Disaster Management (2026)**
- **Objective:** Analyze architectures and technologies for self-healing emergency communication networks.[^15]
- **Methodology:** Comprehensive review of wireless mesh networks, AI-based routing algorithms (DSR, AODV), and edge computing integration for fault tolerance.[^15]
- **Key Results:** Self-healing networks demonstrated significant improvement in communication reliability during simulated disaster scenarios. AI routing optimized data transmission, reduced latency, and prevented congestion.[^15]
- **Limitations:** Primarily theoretical analysis; real-world disaster validation is limited. The energy and carbon costs of running AI routing algorithms on battery-powered nodes are not evaluated.[^15]

### 2.6.2 Gaps and Limitations

- Disaster WSN deployments are overwhelmingly **single-hazard** systems (flood-only, earthquake-only); integrated multi-hazard systems with adaptive data reduction are rare.[^40][^38]
- **Self-healing routing is not integrated into disaster monitoring architectures** — most systems assume that the monitoring network will survive the disaster it is designed to detect.[^41][^40]
- **No disaster WSN study considers carbon-awareness or lifecycle sustainability** — "green" in this context uniformly means low operational energy, not holistic environmental impact.[^43]
- The **6G backhaul integration** for disaster WSNs is entirely unexplored; current systems rely on ZigBee, Wi-Fi, or LoRa with no path toward next-generation connectivity.[^40][^38]
- **Data reduction techniques are absent from disaster monitoring WSN designs** — all surveyed systems transmit raw or minimally processed sensor data, leading to energy waste and shortened deployment lifetimes.[^42][^38]

***

## Cross-Thematic Gap Analysis

The literature review reveals several overarching gaps that the proposed research topic "Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for 6G-Integrated Disaster Sensor Networks: A Lifecycle-Sustainable Approach" is uniquely positioned to address:

| Gap | Themes Affected | Current State |
|-----|----------------|---------------|
| No carbon-aware data reduction or routing in WSNs | 2.1, 2.3, 2.5 | Carbon-aware scheduling exists only for cloud/HPC[^30][^32]; WSN routing optimizes only energy/latency[^14][^16] |
| No integrated autonomic framework for disaster WSNs | 2.2, 2.3, 2.6 | Self-* properties studied in isolation[^10]; disaster WSNs lack self-healing routing[^41][^40] |
| No lifecycle-sustainable sensor network design | 2.5, 2.6 | LCA applied to ICT networks[^29] and individual sensors[^31], but not to full disaster WSN deployments |
| No 6G integration with disaster sensor tiers | 2.4, 2.6 | 6G slicing for smart cities[^23] but not for degraded-infrastructure disaster scenarios |
| No adaptive data reduction for bursty disaster data | 2.1, 2.6 | Data reduction assumes stationary data[^3]; disaster systems transmit raw data[^38] |
| No circular economy framework for sensor node hardware | 2.5 | Circular economy for consumer electronics[^37] but not for WSN hardware design |

***

## Representative References

### Data Reduction in WSNs
- Dias, G.M., Bellalta, B. & Oechsner, S. (2016). *A Survey About Prediction-Based Data Reduction in Wireless Sensor Networks*. ACM Computing Surveys, 49(3). [Link](https://dl.acm.org/doi/10.1145/2996356)[^2]
- Dias, G.M., Bellalta, B. & Oechsner, S. (2017). *The Impact of Dual Prediction Schemes on the Reduction of the Number of Transmissions in Sensor Networks*. Computer Communications, 112. [Link](http://arxiv.org/abs/1509.08778)[^3]
- Xu, X., Ansari, R. & Khokhar, A. (2012). *Power-Efficient Hierarchical Data Aggregation Using Compressive Sensing in WSN*. arXiv:1210.3876. [Link](https://arxiv.org/abs/1210.3876)[^6]
- Pioli, L. et al. (2022). *An Overview of Data Reduction Solutions at the Edge of IoT Systems*. Computing, 104(8), 1867–1889. [Link](https://pmc.ncbi.nlm.nih.gov/articles/PMC8958485/)[^8]
- Nature Scientific Reports (2025). *Compressive Sensing Techniques Based on Secure Data Aggregation*. [Link](https://www.nature.com/articles/s41598-025-14959-0)[^7]

### Autonomous WSN
- Portocarrero, J.M.T. et al. (2014). *Autonomic Wireless Sensor Networks: A Systematic Literature Review*. Journal of Sensors. [Link](https://onlinelibrary.wiley.com/doi/10.1155/2014/782789)[^10]
- Nature Scientific Reports (2025). *Self-Organizing Complex Networks with AI-Driven Adaptive Nodes*. [Link](https://www.nature.com/articles/s41598-025-28035-0)[^12]

### Self-Healing and Adaptive Routing
- Shyama, M., Pillai, A.S. & Anpalagan, A. (2022). *Self-Healing and Optimal Fault-Tolerant Routing in WSNs Using GSO*. Computer Networks, 207. [Link](https://www.sciencedirect.com/science/article/pii/S1389128622003930)[^14]
- Gayathri, M. & Snigdha, V.V. (2025). *SHEER: Self-Healing and Energy-Efficient Cluster-Based Routing for Sustainable WSNs*. Frontiers in Communications and Networks, 6. [Link](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2025.1602928/full)[^16]
- Abba, S. & Lee, J.-A. (2015). *ASAART: An Autonomous Self-Aware and Adaptive Fault-Tolerant Routing Technique for WSNs*. Sensors, 15(8), 20316–20354. [Link](https://pmc.ncbi.nlm.nih.gov/articles/PMC4570424/)[^17]
- Soltani, P. et al. (2025). *Energy-Efficient Routing Algorithm for WSNs: A Multi-Agent RL Approach*. arXiv:2508.14679. [Link](https://arxiv.org/abs/2508.14679)[^19]
- Lee, J.-H. & Jung, I.-B. (2010). *ARF: Adaptive Routing Protocol for Fast Recovery from Large-Scale Failure*. Sensors, 10(4), 3389–3410. [Link](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274226/)[^18]

### 6G Integration
- IJRASET (2025). *Wireless Sensor Networks for IoT and 6G*. [Link](https://www.ijraset.com/research-paper/wireless-sensor-networks-for-iot-and-6g)[^21]
- Alwakeel, A.M. & Alnaim, A.K. (2024). *Network Slicing in 6G: A Strategic Framework for IoT in Smart Cities*. Sensors, 24(13), 4254. [Link](https://pmc.ncbi.nlm.nih.gov/articles/PMC11243923/)[^23]
- Sasan, Z. & Khorsandi, S. (2025). *Balancing Resource Utilization and Slice Dissatisfaction Through Dynamic Soft Slicing for 6G*. Scientific Reports, 15, 22987. [Link](https://www.nature.com/articles/s41598-025-06521-9)[^24]

### Sustainability and Carbon-Awareness
- Ruiz, D. et al. (2022). *Life Cycle Inventory and Carbon Footprint Assessment of Wireless ICT Networks*. Resources, Conservation and Recycling. [Link](https://www.sciencedirect.com/science/article/pii/S0921344921005607)[^44]
- Wagih, M. (2024). *Environmental Life-Cycle Assessment (LCA) of Wireless Sensors*. IEEE. [Link](https://ieeexplore.ieee.org/iel8/9171629/10803549/10703165.pdf)[^31]
- Piastou, M. (2026). *Green Software Development Using Carbon-Aware Scheduling Techniques*. Latin-American Journal of Computing, 13(1). [Link](https://lajc.epn.edu.ec/index.php/LAJC/article/view/463)[^30]
- Nature Scientific Reports (2025). *EAVM Protocol for Green IoT WSNs*. [Link](https://www.nature.com/articles/s41598-025-28783-z)[^33]

### Disaster Monitoring
- Benkhelifa, I., Nouali-Taboudjemat, N. & Moussaoui, S. *Disaster Management Projects Using WSNs: An Overview*. [Link](https://asjp.cerist.dz/en/downArticle/134/23/1/23926)[^39]
- Amrita University. *Real-Time Landslide Warning Systems*. [Link](https://www.amrita.edu/center/awna/landslide/)[^41]
- DOAJ (2025). *Disaster Management-Based IoT Using WSNs* (Flood Monitoring). [Link](https://doaj.org/article/07fefa00ddd2431ab45030b73a1bf92f)[^40]
- Self-Healing Emergency Networks for Disaster Management (2026). [Link](https://www.scribd.com/document/963382587/12)[^15]

---

## References

1. [Data Reduction Techniques in Wireless Sensor Network](https://www.rroij.com/open-access/data-reduction-techniques-in-wireless-sensornetwork-a-survey.pdf)

2. [A Survey About Prediction-Based Data Reduction in Wireless ...](https://dl.acm.org/doi/10.1145/2996356) - In this work, we analyze and categorize existing prediction-based data reduction mechanisms that hav...

3. [The Impact of Dual Prediction Schemes on the Reduction of the Number of Transmissions in Sensor Networks](http://arxiv.org/abs/1509.08778) - Future Internet of Things (IoT) applications will require that billions of wireless devices transmit...

4. [Evaluation of Deep Learning Methods in a Dual Prediction Scheme to Reduce Transmission Data in a WSN](https://lume.ufrgs.br/bitstream/handle/10183/232698/001133840.pdf;jsessionid=EB4985FADCED6313C0997D3ACDFCFDCF?sequence=1)

5. [Data Reduction Techniques in Wireless Sensor Networks ... - ijisae.org](https://ijisae.org/index.php/IJISAE/article/view/4098) - In this piece, we focused our attention largely on the energy consumption of sensor nodes and the re...

6. [Power-efficient Hierarchical Data Aggregation using Compressive Sensing in WSN](https://arxiv.org/abs/1210.3876) - Compressive Sensing (CS) method is a burgeoning technique being applied to diverse areas including w...

7. [Compressive sensing techniques based on secure data aggregation ...](https://www.nature.com/articles/s41598-025-14959-0) - The WSN suffers from the energy-limited sensor nodes, which consume energy heavily depending upon th...

8. [An overview of data reduction solutions at the edge of IoT systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC8958485/) - Throughout this research question, we can understand, in general, which are the most used techniques...

9. [Lightweight Signal Processing and Edge AI for Real-Time ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12610206/) - The proliferation of IoT devices has created vast sensor networks that generate continuous time-seri...

10. [Autonomic Wireless Sensor Networks: A Systematic Literature Review](https://onlinelibrary.wiley.com/doi/10.1155/2014/782789) - In this systematic literature review (SLR) we aim to provide an overview of existing WSN middleware ...

11. [A Genetic Algorithm with Self-Configuration Chromosome for the Optimization of Wireless Sensor Networks](https://dl.acm.org/doi/10.1145/2684103.2684132) - In typical applications of sensor networks, unattended sensors are randomly deployed. It is essentia...

12. [Self-organizing complex networks with AI-driven adaptive nodes for ...](https://www.nature.com/articles/s41598-025-28035-0) - In this study, we introduce an Artificial Intelligence (AI)-enhanced self-organizing network model, ...

13. [Sensor Autonomy: Enabling Self-Configuring and Self-Healing Sensor Networks - Wireless Sensor Networks Research Group](https://sensor-networks.org/sensor-autonomy-enabling-self-configuring-and-self-healing-sensor-networks/) - Sensor networks have evolved significantly in recent years, driven by advancements in microelectroni...

14. [Self-healing and optimal fault tolerant routing in wireless sensor networks using genetical swarm optimization](https://www.sciencedirect.com/science/article/pii/S1389128622003930) - A wireless sensor network (WSN) is used in area monitoring, surveillance, virtual reality, artificia...

15. [Self-Healing Networks for Disaster Management | PDF - Scribd](https://www.scribd.com/document/963382587/12) - Communication, Wireless Mesh Network, Disaster healing or corrective action happens autonomously.

16. [Frontiers | Self-healing and energy-efficient cluster-based routing for sustainable wireless sensor networks](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2025.1602928/full) - Wireless sensor networks (WSNs) are extensively employed in various applications like environmental ...

17. [An Autonomous Self-Aware and Adaptive Fault Tolerant Routing Technique for Wireless Sensor Networks](https://pmc.ncbi.nlm.nih.gov/articles/PMC4570424/) - We propose an autonomous self-aware and adaptive fault-tolerant routing technique (ASAART) for wirel...

18. [Speedy Routing Recovery Protocol for Large Failure Tolerance in Wireless Sensor Networks](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274226/) - Wireless sensor networks are expected to play an increasingly important role in data collection in h...

19. [Energy-Efficient Routing Algorithm for Wireless Sensor Networks](https://arxiv.org/abs/2508.14679) - This paper presents a novel method using reinforcement learning-based cluster-head selection and a h...

20. [Improving the functionality of wireless sensor networks through the ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12370893/) - To improve the routing and data transmission of wireless sensor networks, this study recommends util...

21. [A Wireless Sensor Networks for IoT and 6G - IJRASET](https://www.ijraset.com/research-paper/wireless-sensor-networks-for-iot-and-6g) - Wireless Sensor Networks (WSNs) have emerged as a core technology for making intelligent environment...

22. [6G wireless networks and terahertz communications](https://journalwjarr.com/content/6g-wireless-networks-and-terahertz-communications-intelligent-reflecting-surfaces-mimo-and) - The advent of 6G wireless networks marks a paradigm shift in wireless communication, aiming to achie...

23. [Network Slicing in 6G: A Strategic Framework for IoT ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC11243923/) - The emergence of 6G communication technologies brings both opportunities and challenges for the Inte...

24. [Balancing resource utilization and slice dissatisfaction ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12217554/) - Next-generation networks must address challenges such as exponential user growth, escalating traffic...

25. [Terahertz Communication – The Next Frontier for 6G Networks](https://www.rfpage.com/terahertz-communication/) - Race to 6G networks is already established, and one of the technologies that is continuously proving...

26. [Terahertz Communication for a 6G Future](https://resources.pcb.cadence.com/blog/2023-terahertz-communication-for-a-6g-future) - Discover the possibilities of terahertz communication for 6G, unlocking high-speed wireless connecti...

27. [Sub-terahertz communication in 6G - Ericsson](https://www.ericsson.com/en/6g/spectrum/sub-thz) - Serving up very high data rates and low latencies, communication in the sub-terahertz (sub-THz) rang...

28. [Future Wireless Communication Technology towards 6G IoT - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9103828/) - This article adopts the vision for 6G IoT systems and proposes an IoT-based real-time location monit...

29. [[PDF] Life cycle inventory and carbon footprint assessment of wireless ICT ...](https://wiki.ietf.org/1-s2.0-s0921344921005607-main.pdf)

30. [Green software development using Carbon-Aware Scheduling ...](https://lajc.epn.edu.ec/index.php/LAJC/article/view/463) - The objective of the present paper is to systematize contemporary approaches of green software devel...

31. [Environmental Life-Cycle Assessment (LCA) of Wireless ...](https://ieeexplore.ieee.org/iel8/9171629/10803549/10703165.pdf) - by M Wagih · 2024 · Cited by 14 — In an active microwave system, over 80% of the embodied carbon (du...

32. [[PDF] Green HPC: Carbon-Aware Scheduling in Cloud Data Centers](https://ijeret.org/index.php/ijeret/article/download/272/259) - Green HPC encompasses a wide range of technologies, including Variable Voltage And Frequency (DVFS),...

33. [Energy-Aware adaptive virtualization and migration protocol for ...](https://www.nature.com/articles/s41598-025-28783-z) - The primary objective of this study is to present an EAVM protocol for Green IoT Wireless Sensor Net...

34. [Energy harvesting in self-sustainable IoT devices - A survey](https://www.sciencedirect.com/science/article/abs/pii/S1389128623004565) - This paper tries to fill the gap between IoT applications and the self-sustainable IoT system design...

35. [Edge Computing and Sustainability: Reducing Carbon Footprints](https://snuc.com/blog/edge-computing-and-sustainability/) - Explore the edge computing environmental impact and how it promotes sustainability by reducing energ...

36. [Review Driving sustainable circular economy in electronics: A comprehensive review on environmental life cycle assessment of e-waste recycling ☆](https://www.sciencedirect.com/science/article/abs/pii/S0269749123020833) - E-waste, encompassing discarded materials from outdated electronic equipment, often ends up intermix...

37. [How circular economy models can address global e-waste](https://www.ey.com/en_us/insights/climate-change-sustainability-services/how-circular-economy-models-can-address-global-e-waste) - Electronic waste creates a $57 billion loss annually. Adopting circular models can help firms access...

38. [International Journal for Multidisciplinary Research (IJFMR)](https://ijfmr.com/papers/2024/6/31605.pdf)

39. [[PDF] Disaster Management Projects using Wireless Sensor Networks](https://asjp.cerist.dz/en/downArticle/134/23/1/23926)

40. [Disaster management-based internet of things using ...](https://doaj.org/article/07fefa00ddd2431ab45030b73a1bf92f) - Wireless Sensor Networks (WSNs) have become essential in the monitoring and managing environmental d...

41. [Real-time Landslide Warning Systems - Amrita Vishwa Vidyapeetham](https://www.amrita.edu/center/awna/landslide/)

42. [[PDF] Smart Disaster Detection and Evacuation Alert System Using ... - IJIRT](https://ijirt.org/publishedpaper/IJIRT178967_PAPER.pdf) - 1.2 ADVANTAGES. The system offers real-time monitoring of soil moisture, rainfall, and vibrations to...

43. [Greener disaster alerts: Low-energy wireless sensor networks warn of hurricanes, earthquakes](https://www.sciencedaily.com/releases/2011/06/110627134527.htm) - New software allows wireless sensor networks to run at much lower energy, according to researchers. ...

44. [Life cycle inventory and carbon footprint assessment of ...](https://www.sciencedirect.com/science/article/pii/S0921344921005607) - by D Ruiz · 2022 · Cited by 50 — The aim of this work is to quantify, assess, and identify hotspots ...


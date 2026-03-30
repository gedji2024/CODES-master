# Code Repositories and Baseline Implementations for Carbon-Aware 6G Disaster Sensor Networks

This document catalogs open-source code repositories, simulation environments, and implementation tools suitable as baselines for the PhD research topic: *"Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for 6G-Integrated Disaster Sensor Networks."* Each entry includes a summary of functionality, programming language, strengths, limitations, and notes on suitability for baseline comparison.

***

## Category 1: AI/ML-Based Routing Algorithm Codebases

### 1.1 EER-RL — Energy-Efficient Routing via Reinforcement Learning

| Field | Detail |
|-------|--------|
| **Repository** | [viallykaz/EER-RL](https://github.com/viallykaz/EER-RL) (GitHub) / [MATLAB Central](https://www.mathworks.com/matlabcentral/fileexchange/94685-eer-rl) |
| **Language** | MATLAB |
| **Functionality** | Implements EER-RL, an energy-efficient routing protocol for IoT-WSNs using reinforcement learning. RL agents adapt to network changes (mobility, energy level) and improve routing decisions over time[^1]. |
| **Strengths** | Published and peer-reviewed (Mobile Information Systems, 2021). Directly compares with existing energy-efficient routing protocols. Clean MATLAB implementation suitable for benchmarking network lifetime, energy efficiency, and scalability[^1]. |
| **Limitations** | MATLAB-only; not easily integrated with NS-3 or OMNeT++ simulations. No self-healing or fault-tolerance component. No carbon-awareness[^2]. |
| **Suitability** | **High** — strong baseline for comparing RL-based routing energy efficiency against a carbon-aware extension. |

### 1.2 Q-Routing Protocol — RL for Dynamic Networks

| Field | Detail |
|-------|--------|
| **Repository** | [Duncanswilson/q-routing-protocol](https://github.com/Duncanswilson/q-routing-protocol) |
| **Language** | Python (+ C), OpenAI Gym |
| **Functionality** | Python port of the seminal Boyan & Littman Q-routing paper. Implements Q-learning and SARSA agents on a dynamic network simulator with fluctuating edge weights and disappearing links[^3]. |
| **Strengths** | Clean Gym-based environment enables rapid RL experimentation. Supports dynamic topology changes (edge failures, weight fluctuations) — partially simulates disaster-like disruptions. Modular agent design allows swapping RL algorithms[^3]. |
| **Limitations** | Generic network routing, not WSN-specific. No energy model, no sensor node constraints, no clustering[^3]. |
| **Suitability** | **Medium** — useful as an RL routing framework to extend with WSN energy models and carbon-aware reward functions. |

### 1.3 RL Routing Protocol for UAV Networks

| Field | Detail |
|-------|--------|
| **Repository** | [edu-rinaldi/RL-Routing-Protocol](https://github.com/edu-rinaldi/RL-Routing-Protocol) |
| **Language** | Python |
| **Functionality** | UAV-Networks-Routing simulator for experimenting with AI-based routing protocols on unmanned aerial vehicle networks. Implements Q-learning-based geo-routing with configurable network topologies[^4]. |
| **Strengths** | Built-in mobility model and visualization. Modular routing algorithm plug-in architecture — easy to implement and compare new protocols. Directly relevant to disaster-response UAV-sensor relay scenarios[^4]. |
| **Limitations** | UAV-focused; does not model ground-level WSN constraints (battery depletion, sensor duty cycling). No energy harvesting or carbon metrics[^4]. |
| **Suitability** | **Medium** — relevant for hybrid UAV-WSN disaster architectures; can be extended with ground sensor tiers. |

### 1.4 DQN for Packet Routing on Dynamic Networks

| Field | Detail |
|-------|--------|
| **Repository** | [cnktran/Reinforcement-Learning-Approach-to-Packet-Routing](https://github.com/cnktran/Reinforcement-Learning-Approach-to-Packet-Routing-on-a-Dynamic-Network) |
| **Language** | Python (PyTorch, NetworkX, OpenAI Gym) |
| **Functionality** | Simulates packet routing on dynamic networks with randomly disappearing edges and sinusoidal weight fluctuations. Implements Dijkstra, Floyd-Warshall, Q-learning, and Deep Q-Learning routing agents[^5]. |
| **Strengths** | Multiple baseline algorithms (shortest path, Q-learning, DQN) in a single framework for direct comparison. Dynamic topology changes simulate disaster-like link failures. Performance metrics include delivery time and congestion[^5]. |
| **Limitations** | Not WSN-specific. No energy model or node death simulation. Requires adaptation for sensor network constraints[^5]. |
| **Suitability** | **Medium-High** — excellent RL routing testbed; adding WSN energy models and carbon-aware rewards would create a strong baseline comparison framework. |

### 1.5 RL-Based Routing for SDN Networks

| Field | Detail |
|-------|--------|
| **Repository** | [davidcamilo0710/Routing_Reinforcement_Learning](https://github.com/davidcamilo0710/Routing_Reinforcement_Learning) |
| **Language** | Python |
| **Functionality** | RL-based routing for SDN networks that classifies flows as "elephant" (high bandwidth) or "mouse" (low bandwidth) and routes accordingly using Q-learning[^6]. |
| **Strengths** | Demonstrates differentiated routing by flow type — conceptually analogous to differentiating disaster-critical vs. routine sensor data. Achieves ~90% accuracy on small topologies[^6]. |
| **Limitations** | SDN-oriented; not directly applicable to distributed WSN without significant adaptation. Small scale[^6]. |
| **Suitability** | **Low-Medium** — useful conceptually for traffic-aware routing ideas but requires substantial WSN adaptation. |

***

## Category 2: LEACH and Clustering Protocol Implementations

### 2.1 LEACH on OMNeT++/INET (PiLeachProtocol)

| Field | Detail |
|-------|--------|
| **Repository** | [xcodeBn/PiLeachProtocol](https://github.com/xcodeBn/PiLeachProtocol) |
| **Language** | C++ (OMNeT++ 6.0, INET 4.5) |
| **Functionality** | Full LEACH protocol implementation for OMNeT++/INET. Includes probabilistic CH election, dynamic clustering, TDMA scheduling, and data aggregation forwarding to base station[^7]. |
| **Strengths** | Runs on the latest OMNeT++/INET stack (6.0/4.5). Full protocol-layer simulation with IEEE 802.15.4 support. Energy consumption tracking via INET's energy framework. Visualization of cluster formation[^7]. |
| **Limitations** | Standard LEACH without self-healing, fault tolerance, or multi-hop extensions. No carbon or lifecycle sustainability metrics[^7]. |
| **Suitability** | **High** — primary clustering baseline. Proposed carbon-aware routing can be directly benchmarked against this LEACH implementation on OMNeT++. |

### 2.2 LEACH on OMNeT++ (Agr-IoT)

| Field | Detail |
|-------|--------|
| **Repository** | [Agr-IoT/LEACH](https://github.com/Agr-IoT/LEACH) |
| **Language** | C++ (OMNeT++ 5.6.2, INET 4.2.5) |
| **Functionality** | IEEE 802.15.4-based LEACH implementation with CSMA for setup phase and slotted TDMA for steady state. Includes detailed setup instructions[^8]. |
| **Strengths** | Well-documented, tested OMNeT++/INET integration. Realistic PHY/MAC layer interaction through IEEE 802.15.4 standard[^8]. |
| **Limitations** | Older OMNeT++/INET versions. No advanced CH selection (energy-aware, distance-aware). No fault tolerance[^8]. |
| **Suitability** | **High** — classic LEACH baseline for comparing proposed improvements in CH selection and self-healing. |

### 2.3 LEACH on NS-3

| Field | Detail |
|-------|--------|
| **Repository** | [wakwanza/leach](https://github.com/wakwanza/leach) |
| **Language** | C++ (NS-3.19) |
| **Functionality** | NS-3 implementation of LEACH clustering protocol simulating energy profiles and network lifetime of WSNs[^9]. |
| **Strengths** | NS-3-based, enabling integration with NS-3's extensive wireless models (propagation, mobility, energy). 53 GitHub stars indicate community validation. MIT licensed[^9]. |
| **Limitations** | Hard-coded configuration. Only tested with NS-3.19 (current version is 3.47). May require porting effort[^9][^10]. |
| **Suitability** | **Medium-High** — useful NS-3 baseline if porting to current NS-3 version is feasible. |

### 2.4 LEACH in Python

| Field | Detail |
|-------|--------|
| **Repository** | [Nachi28/WSN_LEACH](https://github.com/Nachi28/WSN_LEACH) |
| **Language** | Python (NumPy, Matplotlib, pandas) |
| **Functionality** | Lightweight Python WSN simulation using LEACH. Models sensor nodes, energy consumption, packet loss, and cluster head formation. Outputs PDR and E2E delay to Excel[^11]. |
| **Strengths** | Easy to modify and extend in Python. Generates publication-ready metrics (PDR, E2E delay). Low barrier to entry for rapid prototyping[^11]. |
| **Limitations** | Simplified radio and MAC models. Not suitable for protocol-accurate simulation. No physical layer realism[^11]. |
| **Suitability** | **Medium** — good for rapid algorithm prototyping and initial carbon-aware reward function experiments before moving to OMNeT++/NS-3. |

### 2.5 LEACH in MATLAB

| Field | Detail |
|-------|--------|
| **Repository** | [Ilia-Abolhasani/leach](https://github.com/Ilia-Abolhasani/leach) |
| **Language** | MATLAB |
| **Functionality** | Simulates LEACH-based routing protocols with random network generation, distance calculations, energy consumption tracking, and dead node counting[^12]. |
| **Strengths** | Modular MATLAB codebase. Direct comparison between LEACH and direct communication protocol. Clear energy model implementation[^12]. |
| **Limitations** | MATLAB dependency. No advanced features (multi-hop, fault tolerance, ML integration)[^12]. |
| **Suitability** | **Medium** — MATLAB baseline for initial comparison with AI-based CH selection methods. |

***

## Category 3: WSN Simulation Environments

### 3.1 NS-3 — Network Simulator 3

| Field | Detail |
|-------|--------|
| **Repository** | [nsnam/ns-3-dev-git](https://github.com/nsnam/ns-3-dev-git) / [nsnam.org](https://www.nsnam.org) |
| **Language** | C++, Python bindings |
| **Functionality** | Discrete-event network simulator for Internet systems. Current version 3.47 includes Wi-Fi, LTE, 5G NR, ZigBee, 6LoWPAN modules, plus a comprehensive energy framework with battery models, energy harvesting, and device energy models[^10][^13]. |
| **Strengths** | Industry-standard simulator with extensive protocol support. Built-in energy framework supporting BasicEnergySource, GenericBatteryModel, supercapacitors, and energy harvesters (solar, RF)[^13]. Active community with regular releases. Python bindings for scripting[^10]. |
| **Limitations** | Steep learning curve. No native WSN-specific clustering protocols (LEACH, etc.) — must be added via modules like BATSEN[^14]. Computationally expensive for large-scale simulations[^10]. |
| **Suitability** | **Very High** — recommended primary simulation platform for protocol-accurate evaluation of proposed routing algorithms, energy models, and disaster scenarios. |

### 3.2 BATSEN — NS-3 WSN Modules

| Field | Detail |
|-------|--------|
| **Repository** | [npowell3/BATSEN](https://github.com/npowell3/BATSEN) |
| **Language** | C++, Python (NS-3) |
| **Functionality** | Open-source NS-3 modules specifically for WSN simulation. Includes BATMAN routing protocol module, aggregator statistics collection, and a sensor module supporting both centrally controlled LEACH and BATSEN implementations[^14]. |
| **Strengths** | Purpose-built WSN abstraction layer for NS-3. Combines routing, aggregation, and sensing in a unified framework. GPL-3.0 licensed[^14]. |
| **Limitations** | Small community (10 stars). May require updates for latest NS-3. Limited documentation[^14]. |
| **Suitability** | **High** — extends NS-3 with WSN-specific capabilities directly relevant to the proposed research. |

### 3.3 NS-3 Energy Harvesting Module

| Field | Detail |
|-------|--------|
| **Repository** | [nsnam/ns-3-dev-git/energy](https://github.com/nsnam/ns-3-dev-git/blob/master/examples/energy/energy-model-with-harvesting-example.cc) / [signetlabdei/capacitor-ns3](https://github.com/signetlabdei/capacitor-ns3) |
| **Language** | C++ (NS-3) |
| **Functionality** | NS-3's built-in energy framework supports BasicEnergyHarvester (random variable power), real-data harvesters, and battery/capacitor models. The capacitor-ns3 extension adds batteryless capacitor-based IoT nodes with LoRaWAN integration[^13][^15]. |
| **Strengths** | Native NS-3 integration. The capacitor model is peer-reviewed (WNS3 2021). Supports trace-driven energy harvesting from real measurement datasets[^15][^16]. |
| **Limitations** | BasicEnergyHarvester is simplistic. Capacitor model only tested with LoRaWAN. No carbon-intensity coupling[^13]. |
| **Suitability** | **High** — essential for modeling energy-harvesting disaster sensor nodes; can be extended with carbon-intensity data feeds. |

### 3.4 OMNeT++ with INET Framework

| Field | Detail |
|-------|--------|
| **Repository** | [inet-framework/inet](https://github.com/inet-framework/inet) / [omnetpp.org](https://omnetpp.org) |
| **Language** | C++ (NED language for topology) |
| **Functionality** | Open-source communication networks simulation package for OMNeT++. Provides models for wired/wireless/mobile networks including IEEE 802.15.4, IPv6, 6LoWPAN, energy models, and mobility[^17]. An energy model framework allows evaluation of radio transceiver and CPU energy consumption with calibration to real hardware[^18]. |
| **Strengths** | Modular architecture with excellent visualization. Energy model distinguishes power consumption in each radio state and transition energy. Calibratable to real sensor hardware (e.g., CC2420 transceiver)[^18]. Large ecosystem of community extensions[^17]. |
| **Limitations** | OMNeT++ academic license is free but commercial use requires licensing. Learning curve for NED language. Less 5G/6G support than NS-3[^17]. |
| **Suitability** | **Very High** — primary alternative to NS-3. Especially suited for detailed WSN protocol simulation with LEACH implementations already available[^7][^8]. |

### 3.5 Contiki-NG with Cooja Simulator

| Field | Detail |
|-------|--------|
| **Repository** | [contiki-ng/contiki-ng](https://github.com/contiki-ng/contiki-ng) |
| **Language** | C (OS), Java (Cooja simulator) |
| **Functionality** | Open-source OS for IoT devices with native support for IPv6/6LoWPAN, 6TiSCH, RPL, and CoAP. Cooja provides network-level simulation with emulated hardware (Sky/Tmote motes). 1.4k GitHub stars, 219 contributors, active releases (v5.0, Dec 2024)[^19][^20]. |
| **Strengths** | Code runs on actual hardware OR in simulation — same binary. Native RPL implementation is the de facto IoT routing baseline. Cooja visualizes radio range, interference, and packet exchanges in real-time[^21][^19]. Widely used in published WSN research. |
| **Limitations** | Primarily targets constrained devices (MSP430, ARM Cortex-M). Limited to 6LoWPAN/RPL stack — no native LEACH or custom clustering. No built-in energy harvesting simulation. Cooja performance degrades beyond ~100 nodes[^19]. |
| **Suitability** | **High** — essential for RPL baseline comparisons and for validating proposed protocols on realistic IoT firmware before hardware deployment. |

### 3.6 CupCarbon — WSN & Smart City Simulator

| Field | Detail |
|-------|--------|
| **Repository** | [thisislola/cupcarbon-v3](https://github.com/thisislola/cupcarbon-v3) / [cupcarbon.com](http://cupcarbon.com/) |
| **Language** | Java (JavaFX GUI) |
| **Functionality** | Multi-agent WSN simulator with OpenStreetMap integration. Supports natural event generation (fires, gas), mobile agents (vehicles, UAVs), sensor programming via SenScript, and energy/battery consumption graphing[^22][^23]. |
| **Strengths** | Unique ability to simulate environmental disaster events (fire propagation, gas spread) overlaid on real geographic maps. Visualizes energy consumption and battery levels. Educational and prototyping-friendly[^24][^23]. |
| **Limitations** | Does not implement full protocol layers — complements rather than replaces NS-3/OMNeT++. Limited scalability for large networks. SenScript is a custom language with limited community[^23]. |
| **Suitability** | **Medium-High** — valuable for disaster scenario visualization and prototyping before detailed protocol simulation. Useful for generating disaster event traces to feed into NS-3/OMNeT++ simulations. |

### 3.7 FIT IoT-LAB — Physical Testbed

| Field | Detail |
|-------|--------|
| **Platform** | [iot-lab.info](https://www.iot-lab.info) |
| **Language** | C (Contiki-NG/RIOT firmware), Python (tools) |
| **Functionality** | Large-scale open wireless sensor network testbed with 1,500+ nodes across six sites in France. Supports MSP430, STM32, and Cortex-A8 architectures with 802.15.4 radios. Provides remote firmware deployment, power consumption measurement, and radio monitoring[^25][^26]. |
| **Strengths** | Real hardware validation — bridges the simulation-to-deployment gap. Free and open-access. Built-in power consumption measurement infrastructure. Supports Contiki-NG, RIOT, and bare-metal firmware[^26]. |
| **Limitations** | Fixed indoor deployments — cannot replicate outdoor disaster conditions. Limited to available node types. Requires internet connectivity for remote access[^25]. |
| **Suitability** | **Medium-High** — recommended for real-hardware validation of proposed RPL extensions and energy-efficient protocols after simulation-based development. |

***

## Category 4: Carbon-Awareness and Sustainability Tools

### 4.1 Carbon Aware SDK — Green Software Foundation

| Field | Detail |
|-------|--------|
| **Repository** | [Green-Software-Foundation/carbon-aware-sdk](https://github.com/Green-Software-Foundation/carbon-aware-sdk) |
| **Language** | C# (.NET), REST API |
| **Functionality** | SDK for building carbon-aware applications. Provides a unified API and CLI to query real-time and forecast carbon intensity data from electricity grids (via WattTime, Electricity Maps). Enables temporal shifting (run when carbon is low) and spatial shifting (run where carbon is low)[^27][^28]. |
| **Strengths** | Backed by the Green Software Foundation with industry adoption (UBS, Vestas). Standardized API for carbon-intensity queries. Modular plugin architecture. Actively maintained with comprehensive documentation[^28][^29]. |
| **Limitations** | Designed for cloud/data-center workloads, not distributed sensor networks. .NET dependency. Assumes reliable internet access for API calls — not directly usable on constrained IoT nodes[^27]. |
| **Suitability** | **High** — the carbon-intensity data feeds and scheduling logic can be adapted for a gateway/edge-layer carbon-aware decision engine that informs sensor network routing decisions. Core conceptual framework for carbon-aware WSN extension. |

### 4.2 CodeCarbon — Emissions Tracker

| Field | Detail |
|-------|--------|
| **Repository** | [mlco2/codecarbon](https://github.com/mlco2/codecarbon) / [codecarbon.io](https://codecarbon.io) |
| **Language** | Python |
| **Functionality** | Lightweight Python library that estimates hardware electricity consumption (GPU + CPU + RAM) and calculates total carbon emissions based on local grid carbon intensity. Provides online dashboard for visualization[^30][^31]. |
| **Strengths** | Easy `pip install` integration. Automatically detects hardware. Applies region-specific carbon intensity. Dashboard for tracking emissions over time. Widely adopted in ML research community[^30]. |
| **Limitations** | Tracks computational carbon only — does not model embodied carbon, network transmission energy, or sensor node operational carbon. Not designed for embedded/IoT devices[^30]. |
| **Suitability** | **Medium-High** — useful for measuring the carbon cost of training RL routing models and running simulations. Can be integrated into the experimental pipeline to report the computational carbon footprint of proposed algorithms. |

### 4.3 Electricity Maps — Grid Carbon Intensity Data

| Field | Detail |
|-------|--------|
| **Repository** | [electricitymaps/electricitymaps-contrib](https://github.com/electricitymaps/electricitymaps-contrib) |
| **Language** | Python (data parsers), JavaScript (visualization) |
| **Functionality** | Open-source data parsers and visualization for real-time CO₂ emissions of electricity consumption worldwide. Uses flow-tracing to calculate consumption-based carbon intensity across 150+ countries[^32][^33]. |
| **Strengths** | Official data from government TSOs. Consumption-based accounting (not just production). Hourly or better granularity. Free API tier available. AGPL-3.0 licensed open-source parsers[^32]. |
| **Limitations** | Coverage gaps in developing countries where disaster sensor networks are most needed. API rate limits on free tier[^33]. |
| **Suitability** | **Very High** — essential data source for carbon-aware routing decisions. Historical carbon intensity traces can drive simulation experiments; real-time API can power gateway-level carbon-aware scheduling. |

### 4.4 Green Algorithms — Carbon Footprint Calculator

| Field | Detail |
|-------|--------|
| **Repository** | [GreenAlgorithms/green-algorithms-tool](https://github.com/GreenAlgorithms/green-algorithms-tool) / [green-algorithms.org](http://www.green-algorithms.org) |
| **Language** | Python (Streamlit) |
| **Functionality** | Online tool and methodology for estimating the carbon footprint of any computational task. Factors in runtime, hardware TDP, number of cores, memory, local carbon intensity, and PUE. Published in *Advanced Science* (2021)[^34][^35]. |
| **Strengths** | Peer-reviewed methodology. Does not require code modification — inputs are hardware specs and runtime. Useful for reporting carbon footprint of simulation campaigns in publications[^34]. |
| **Limitations** | Post-hoc estimation only; cannot be used for real-time carbon-aware decision-making. Does not model sensor node operational carbon[^36]. |
| **Suitability** | **Medium** — useful for reporting the carbon footprint of simulation experiments in the dissertation. Complements CodeCarbon for comprehensive emissions reporting. |

### 4.5 Electricity Maps IF Plugin

| Field | Detail |
|-------|--------|
| **Repository** | [electricitymaps/if-electricitymaps](https://github.com/electricitymaps/if-electricitymaps) |
| **Language** | TypeScript |
| **Functionality** | Plugin for the Impact Framework (IF) that computes average carbon intensity of electricity consumption for a given time period and location using Electricity Maps API[^37]. |
| **Strengths** | Standardized input/output format. Aggregates hourly carbon data over event durations (up to 10 days). Supports zone-based and coordinate-based queries[^37]. |
| **Limitations** | Requires commercial API token. TypeScript dependency[^37]. |
| **Suitability** | **Medium** — useful for automating carbon intensity calculations in simulation post-processing pipelines. |

***

## Category 5: Data Reduction and Compressive Sensing

### 5.1 Compressive Sensing in WSN (MATLAB)

| Field | Detail |
|-------|--------|
| **Repository** | [manishni30/compressive-sensing](https://github.com/manishni30/compressive-sensing) |
| **Language** | MATLAB |
| **Functionality** | Three-part implementation: basic CS signal recovery, analysis of different measurement matrices, and application of CS to WSN using LEACH clustering. Successfully reconstructs compressed data with low error[^38]. |
| **Strengths** | Directly demonstrates CS applied to LEACH-based WSN. End-to-end pipeline from compression to reconstruction. Simple, well-structured codebase[^38]. |
| **Limitations** | MATLAB-only. Basic LEACH implementation. No energy model or carbon metrics. No adaptive compression based on data dynamics[^38]. |
| **Suitability** | **High** — directly usable as a data reduction baseline for comparing proposed carbon-aware adaptive compression schemes. |

### 5.2 Compressive Sensing in Python

| Field | Detail |
|-------|--------|
| **Repository** | [dimikout3/CompressiveSensingPython](https://github.com/dimikout3/CompressiveSensingPython) |
| **Language** | Python |
| **Functionality** | Python implementation of compressive sensing fundamentals: sparse signal recovery, 1D (sound) and 2D (image) reconstruction from incomplete samples[^39]. |
| **Strengths** | Python-based — easy integration with RL routing frameworks. Demonstrates core CS principles applicable to sensor data[^39]. |
| **Limitations** | Not WSN-specific. No network simulation or energy model. Requires adaptation for multi-hop sensor data aggregation[^39]. |
| **Suitability** | **Medium** — useful as a CS library to integrate into a Python-based WSN simulation for data reduction experiments. |

***

## Category 6: Energy Harvesting Implementations

### 6.1 Energy Harvesting WSN Demoboard

| Field | Detail |
|-------|--------|
| **Repository** | [danielecostarella/energy-harvesting-demoboard](https://github.com/danielecostarella/energy-harvesting-demoboard) |
| **Language** | Arduino/C |
| **Functionality** | Firmware for a WSN demonstration board powered by energy harvesting (piezoelectric, solar, thermoelectric). Optimized for low power consumption[^40]. |
| **Strengths** | Real hardware implementation — bridges simulation to deployment. Multi-source energy harvesting. MIT licensed[^40]. |
| **Limitations** | Single-node prototype; no networking stack. Limited documentation. No simulation interface[^40]. |
| **Suitability** | **Low-Medium** — reference for hardware-level energy harvesting design; not directly useful for network-level simulation. |

### 6.2 EH-WSN Modelica Library

| Field | Detail |
|-------|--------|
| **Repository** | [jankokert/EnergyHarvestingWSN](https://github.com/jankokert/EnergyHarvestingWSN) |
| **Language** | Modelica, Python |
| **Functionality** | Modelica library for modeling and simulating Energy Harvesting Wireless Sensor Nodes (EH-WSN) with multi-physics energy flow[^41]. |
| **Strengths** | Physics-based energy harvesting simulation. Modelica enables multi-domain (electrical, thermal, mechanical) modeling[^41]. |
| **Limitations** | Niche tool (Modelica). Small community. No network-layer simulation[^41]. |
| **Suitability** | **Low** — specialized reference for EH modeling; not integrated with network simulators. |

***

## Category 7: Disaster-Specific Simulation

### 7.1 CupCarbon Forest Fire Detection

| Field | Detail |
|-------|--------|
| **Repository** | [Aeres-u99/forestFire-detection](https://github.com/Aeres-u99/forestFire-detection) |
| **Language** | Java (CupCarbon), SenScript |
| **Functionality** | Simulates forest fire detection using CupCarbon's natural event generator. Implements a master-slave sensor architecture where slaves detect fire events and masters perform preliminary analysis before alerting the base station[^24]. |
| **Strengths** | Complete disaster WSN scenario with event generation, multi-tier sensor architecture, and alert logic. Demonstrates real-world disaster monitoring workflow[^24]. |
| **Limitations** | CupCarbon-specific. Simplistic routing (no energy-aware or self-healing). No data reduction or carbon-awareness[^24]. |
| **Suitability** | **Medium** — useful disaster scenario template for generating fire event traces; routing and data management aspects would need to be reimplemented in NS-3/OMNeT++. |

### 7.2 RPL Attack Simulation (Cooja)

| Field | Detail |
|-------|--------|
| **Repository** | [uu-core/IoT-Attacks-IDS](https://github.com/uu-core/IoT-Attacks-IDS) |
| **Language** | C (Contiki-NG), Python |
| **Functionality** | Framework for simulating network-layer attacks on RPL in Cooja. Supports automated scenario generation, modular attack implementations, and structured data collection[^42]. |
| **Strengths** | Tests RPL resilience under adversarial conditions — analogous to testing self-healing under disaster-induced failures. Automated CSV generation for analysis. Modular attack plug-in architecture[^42]. |
| **Limitations** | Security-focused, not disaster-focused. Attack models (blackhole, selective forwarding) differ from disaster failure models (correlated spatial destruction)[^42]. |
| **Suitability** | **Medium** — the RPL disruption framework can be adapted to simulate disaster-induced node failures instead of malicious attacks. |

***

## Recommended Baseline Stack

Based on the analysis above, the following combination of tools provides the most comprehensive baseline infrastructure for the proposed research:

| Research Component | Primary Tool | Secondary Tool |
|-------------------|-------------|----------------|
| **Network simulation** | NS-3 (v3.47) + BATSEN[^10][^14] | OMNeT++ + INET + PiLeachProtocol[^17][^7] |
| **RPL baseline routing** | Contiki-NG / Cooja[^19] | NS-3 6LoWPAN module |
| **LEACH baseline** | PiLeachProtocol (OMNeT++)[^7] | wakwanza/leach (NS-3)[^9] |
| **RL routing baseline** | Q-routing (Gym-based)[^3] | EER-RL (MATLAB)[^1] |
| **Energy harvesting** | NS-3 energy framework + capacitor-ns3[^13][^15] | OMNeT++ energy model[^18] |
| **Carbon intensity data** | Electricity Maps API[^32] | Carbon Aware SDK[^28] |
| **Emissions tracking** | CodeCarbon[^30] | Green Algorithms[^34] |
| **Disaster scenarios** | CupCarbon (event generation)[^22] | Custom NS-3 failure models |
| **Data reduction baseline** | CS-WSN MATLAB[^38] | CompressiveSensingPython[^39] |
| **Hardware validation** | FIT IoT-LAB[^26] | — |

The proposed research fills a gap that none of these tools individually address: integrating carbon-intensity signals into WSN routing and data reduction decisions. The recommended approach is to build on NS-3 or OMNeT++ as the primary simulation platform, feed carbon-intensity traces from Electricity Maps, implement RL-based routing using the Q-routing/DQN framework patterns, and benchmark against LEACH and EER-RL baselines.

---

## References

1. [EER-RL - File Exchange - MATLAB Central - MathWorks](https://www.mathworks.com/matlabcentral/fileexchange/94685-eer-rl) - In this paper, we propose EER-RL, an energy-efficient routing protocol based on reinforcement learni...

2. [viallykaz/EER-RL: Energy-Efficient Routing Based on ... - GitHub](https://github.com/viallykaz/EER-RL) - In this paper, we propose EER-RL, an energy-efficient routing protocol based on reinforcement learni...

3. [Duncanswilson/q-routing-protocol: final project for cpe 400 ... - GitHub](https://github.com/Duncanswilson/q-routing-protocol) - This repo is a python port of the c implementation of Packet Routing in Dynamically Changing Network...

4. [GitHub - edu-rinaldi/RL-Routing-Protocol: A routing algorithm based on QLearning](https://github.com/edu-rinaldi/RL-Routing-Protocol) - A routing algorithm based on QLearning. Contribute to edu-rinaldi/RL-Routing-Protocol development by...

5. [GitHub - cnktran/Reinforcement-Learning-Approach-to-Packet-Routing-on-a-Dynamic-Network: Packet routing simulation on a dynamic network using Shortest Path Routing, Q-learning, and Deep Q-learning](https://github.com/cnktran/Reinforcement-Learning-Approach-to-Packet-Routing-on-a-Dynamic-Network) - Packet routing simulation on a dynamic network using Shortest Path Routing, Q-learning, and Deep Q-l...

6. [GitHub - davidcamilo0710/routing_reinforcement_learning: Reinforcement Learning (RL)-based routing algorithm for SDN networks created from scratch using Python.](https://github.com/davidcamilo0710/Routing_Reinforcement_Learning) - Reinforcement Learning (RL)-based routing algorithm for SDN networks created from scratch using Pyth...

7. [leach protocol simulation with inet4.5 and omnet++ - GitHub](https://github.com/xcodeBn/PiLeachProtocol) - This project implements the Low-Energy Adaptive Clustering Hierarchy (LEACH) protocol, a classic hie...

8. [GitHub - Agr-IoT/LEACH: Simulation of LEACH routing protocol on OMNET++](https://github.com/Agr-IoT/LEACH) - Simulation of LEACH routing protocol on OMNET++. Contribute to Agr-IoT/LEACH development by creating...

9. [GitHub - wakwanza/leach: ns3 implementation of the LEACH protocol for WSN](https://github.com/wakwanza/leach) - ns3 implementation of the LEACH protocol for WSN. Contribute to wakwanza/leach development by creati...

10. [ns-3 | a discrete-event network simulator for internet systems](https://www.nsnam.org) - a discrete-event network simulator for internet systems

11. [Nachi28/WSN_LEACH: Implementing LEACH protocol in a WSN ...](https://github.com/Nachi28/WSN_LEACH) - This Python code simulates a Wireless Sensor Network (WSN) using the LEACH (Low Energy Adaptive Clus...

12. [Ilia-Abolhasani/leach: MATLAB program to simulate and ... - GitHub](https://github.com/Ilia-Abolhasani/leach) - This MATLAB program simulates the performance of LEACH-based routing protocols for wireless sensor n...

13. [14. Energy Framework — Model Library](https://www.nsnam.org/docs/models/html/energy.html)

14. [npowell3/BATSEN: Open source ns-3 modules for Wireless Sensor ...](https://github.com/npowell3/BATSEN) - Open source ns-3 modules for Wireless Sensor Networks. Includes BATMAN routing protocol module, Aggr...

15. [signetlabdei/capacitor-ns3: An ns-3 implementation of a ... - GitHub](https://github.com/signetlabdei/capacitor-ns3) - This is an ns-3 code including. the implementation of battery-less capacitor-based IoT nodes; the im...

16. [ns-3-dev-git/examples/energy/energy-model-with-harvesting-example.cc at master · nsnam/ns-3-dev-git](https://github.com/nsnam/ns-3-dev-git/blob/master/examples/energy/energy-model-with-harvesting-example.cc) - GitHub read-only mirror of ns-3-dev repository, will be kept in sync with main GitLab.com repository...

17. [INET Framework for the OMNeT++ discrete event simulator](https://github.com/inet-framework/inet) - The INET framework is an open-source communication networks simulation package, written for the OMNE...

18. [An Energy Model for Simulation Studies of Wireless Sensor Networks using OMNeT++](https://www.tkn.tu-berlin.de/bib/chen2009energy/chen2009energy.pdf)

19. [contiki-ng/ at develop - GitHub](https://github.com/contiki-ng/contiki-ng?files=1) - Contiki-NG is an open-source, cross-platform operating system for Next-Generation IoT devices. It fo...

20. [Contiki-NG: The OS for Next Generation IoT Devices - GitHub](https://github.com/contiki-ng/contiki-ng) - Contiki-NG is an open-source, cross-platform operating system for Next-Generation IoT devices. It fo...

21. [Running a RPL network in Cooja](https://docs.contiki-ng.org/en/master/doc/tutorials/Running-a-RPL-network-in-Cooja.html)

22. [GitHub - thisislola/cupcarbon-v3: Just a repo of cupcarbon v3.8.2, the IoT simulator for WSN from CupCarbon.](https://github.com/thisislola/cupcarbon-v3) - Just a repo of cupcarbon v3.8.2, the IoT simulator for WSN from CupCarbon. - thisislola/cupcarbon-v3

23. [[PDF] Evaluation of CupCarbon Network Simulator for Wireless Sensor ...](https://www.oldcitypublishing.com/wp-content/uploads/2025/07/NPAv10n2p1Lopez-Pavon.pdf) - The section presents the main characteristics and functionalities of this network simulator, the gra...

24. [Aeres-u99/forestFire-detection: cupcarbon project - GitHub](https://github.com/Aeres-u99/forestFire-detection) - CupCarbon is a multi-agent and discrete event Wireless Sensor Network (WSN) simulator. ... This simu...

25. [Very large scale open wireless sensor network testbed - FIT IoT-LAB](https://www.iot-lab.info/legacy/index.html) - IoT-LAB provides a very large scale infrastructure facility suitable for testing small wireless sens...

26. [FIT IoT-LAB](https://www.iot-lab.info) - The Very Large Scale IoT Testbed

27. [GitHub - Green-Software-Foundation/carbon-aware-sdk: Carbon-Aware SDK](https://github.com/Green-Software-Foundation/carbon-aware-sdk/) - Carbon-Aware SDK. Contribute to Green-Software-Foundation/carbon-aware-sdk development by creating a...

28. [Green-Software-Foundation/carbon-aware-sdk - GitHub](https://github.com/Green-Software-Foundation/carbon-aware-sdk) - The Carbon Aware SDK is a toolset to help you measure the carbon emissions of your software, in turn...

29. [carbon-aware-sdk/casdk-docs/docs/overview/adopters.md at dev](https://github.com/Green-Software-Foundation/carbon-aware-sdk/blob/dev/casdk-docs/docs/overview/adopters.md) - Carbon-Aware SDK. Contribute to Green-Software-Foundation/carbon-aware-sdk development by creating a...

30. [mlco2/codecarbon: Track emissions from Compute](https://github.com/mlco2/codecarbon) - Estimate and track carbon emissions from your computer, quantify and analyze their impact. CodeCarbo...

31. [Track CO₂ emissions of your algorithms in Python w/ CodeCarbon](https://www.youtube.com/watch?v=r_f9MLZxArk) - Are you concerned about the environmental impact of your algorithms? In this video, we'll show you h...

32. [GitHub - electricitymaps/electricitymaps-contrib: The open source repository for Electricity Maps App and data parsers that enables a real-time visualisation of the CO2 emissions of electricity consumption](http://github.com/electricitymaps/electricitymaps-contrib) - The open source repository for Electricity Maps App and data parsers that enables a real-time visual...

33. [The open source repository for Electricity Maps data ... - GitHub](https://github.com/electricitymaps/electricitymaps-contrib) - This project aims to provide a free, open-source, and transparent visualisation of the electricity d...

34. [Green Algorithms: Quantifying the Carbon Footprint of ...](https://d-nb.info/1232618225/34)

35. [GitHub - GreenAlgorithms/green-algorithms-tool](https://github.com/GreenAlgorithms/green-algorithms-tool) - Contribute to GreenAlgorithms/green-algorithms-tool development by creating an account on GitHub.

36. [Green Algorithms](http://www.green-algorithms.org) - Towards environmentally sustainable computational science

37. [electricitymaps/if-electricitymaps - GitHub](https://github.com/electricitymaps/if-electricitymaps) - The ElectricityMapsCarbonIntensity plugin uses the Electricity Maps API to compute the average carbo...

38. [analysis of compressive sensing in wireless sensor network](https://github.com/manishni30/compressive-sensing) - In result, i am successfully reconstructing compressed data with less error. About. analysis of comp...

39. [Compressive Sensing Imprementation in Python3](https://github.com/dimikout3/CompressiveSensingPython) - In this tutorial I'll be investigating compressed sensing in Python. Since the idea of compressed se...

40. [danielecostarella/energy-harvesting-demoboard - GitHub](https://github.com/danielecostarella/energy-harvesting-demoboard) - WSN Demoboard for Energy Harvesting · Getting Started. To get started with this project, you will ne...

41. [jankokert/EnergyHarvestingWSN - GitHub](https://github.com/jankokert/EnergyHarvestingWSN) - A Modelica library to model and simulate Energy Harvesting Wireless Sensor Nodes (EH-WSN) - jankoker...

42. [uu-core/IoT-Attacks-IDS - GitHub](https://github.com/uu-core/IoT-Attacks-IDS) - RPL Attack Simulation using Cooja (Contiki-NG). This repository builds on the multi-trace repository...


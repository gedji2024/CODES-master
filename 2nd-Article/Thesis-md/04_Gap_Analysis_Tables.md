# Gap Analysis Tables

## Table 1 – Thematic Coverage Across Research Domains

| Theme | Traditional Routing | AI/ML Routing | Self-Healing | 6G Integration | Sustainability | Disaster Monitoring |
|-------|--------------------|---------------|--------------|----------------|-----------------|----------------------|
| Energy Efficiency | ✔ | ✔ | ✘ | ✘ | ✘ | ✘ |
| Adaptive Routing | ✘ | ✔ | ✔ | ✘ | ✘ | ✘ |
| Self-Healing | ✘ | ✘ | ✔ | ✘ | ✘ | ✘ |
| 6G Networks | ✘ | ✘ | ✘ | ✔ | ✘ | ✘ |
| Embodied Carbon | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| Disaster Resilience | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ |

---

## LaTeX Version (Table 1)

```latex
\begin{table}[h!]
\centering
\begin{tabular}{lcccccc}
\hline
\textbf{Theme} & \textbf{Traditional} & \textbf{AI/ML} & \textbf{Self-Healing} & \textbf{6G} & \textbf{Sustainability} & \textbf{Disaster} \\
\hline
Energy Efficiency      & \checkmark & \checkmark &  &  &  &  \\
Adaptive Routing       &  & \checkmark & \checkmark &  &  &  \\
Self-Healing           &  &  & \checkmark &  &  &  \\
6G Networks            &  &  &  & \checkmark &  &  \\
Embodied Carbon        &  &  &  &  &  &  \\
Disaster Resilience    &  &  &  &  &  & \checkmark \\
\hline
\end{tabular}
\caption{Thematic coverage across existing research domains.}
\end{table}

| Category              | Limitation Identified                         | Relevance to Thesis Gap              |
| --------------------- | --------------------------------------------- | ------------------------------------ |
| Traditional routing   | Static procedures, limited adaptability       | Needed for integrated AI routing     |
| AI/ML routing         | Lacks lifecycle sustainability                | Supports carbon-aware design         |
| Self-Healing          | Not evaluated in disaster scenarios           | Gap in resilience integration        |
| 6G paradigm research  | Macro focus, absent sensor-level applications | Gap for sensor-level 6G integration  |
| Sustainability in WSN | Energy only; lacks lifecycle metrics          | Supports integrated sustainability   |
| Disaster WSNs         | Focuses on sensing, not adaptive routing      | Gap for autonomous network solutions |


\begin{table}[h!]
\centering
\begin{tabular}{lll}
\hline
\textbf{Category} & \textbf{Limitation} & \textbf{Gap Relevance} \\
\hline
Traditional routing & Static, limited adaptability & Need integrated AI routing \\
AI/ML routing & Lacks lifecycle sustainability & Carbon-aware design gap \\
Self-Healing & Not evaluated in disasters & Resilience integration gap \\
6G research & Macro focus only & Sensor-level 6G gap \\
Sustainability & Energy only & Lifecycle sustainability gap \\
Disaster WSNs & Sensing-focused & Autonomous routing gap \\
\hline
\end{tabular}
\caption{Summary of limitations in key research categories supporting thesis gap.}
\end{table}
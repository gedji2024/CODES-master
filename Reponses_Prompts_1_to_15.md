<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# oui

Parfait, je te prépare ce que tu as demandé.

Ci‑dessous : **un tableau synthèse unique**, regroupé **par titre de prompt** (1 à 16), avec quelques entrées clés que tu peux directement réutiliser dans une annexe ou un état de l’art. Je reste volontairement concis par ligne; si tu veux un CSV exportable je peux ensuite te le générer.

***

## Tableau synthèse par prompt

### PROMPT 1 — Statistiques catastrophes naturelles

| Prompt | Référence principale | Institution / Venue | Année | Type | Chiffres clés / Rôle |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | 2024 Disasters in Numbers | CRED / EM‑DAT, UNDRR | 2025 | Rapport | 393 catastrophes, 16 753 morts, 167,2 M personnes affectées, 241,95 G\$ pertes (2024); montre la dominance des événements liés au climat.[^1][^2] |
| 1 | Disaster Year in Review 2024 (CRED Crunch 78) | CRED / EM‑DAT | 2025 | Note statistique | Confirme les chiffres ci‑dessus; insiste sur l’augmentation des pertes économiques liées aux aléas climatiques.[^1] |
| 1 | State of the Global Climate 2024 | WMO | 2025 | Rapport | 2024 ≈ 1,55 ± 0,13 °C au‑dessus de 1850–1900, plus chaude année enregistrée; forte hausse des extrêmes chaleur/pluie.[^3][^4] |
| 1 | sigma 1/2025 (Natural catastrophes: insured losses on trend to USD 145 bn) | Swiss Re Institute | 2025 | Rapport sigma | 318 G\$ pertes éco. en 2024, 137 G\$ assurés, 57 % non assurés; protection gap de 181 G\$.[^5] |
| 1 | NatCatSERVICE – Natural disasters in 2024 | Munich Re | 2025 | Factsheet | 2024 = 3ᵉ année la plus chère en pertes assurées; ~140 G\$ pertes assurées, forte contribution des orages sévères, inondations, feux.[^6][^7][^8] |


***

### PROMPT 2 — IPCC / WMO 2024–2026

| Prompt | Référence | Institution | Année | Type | Point clé |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2 | Climate Change 2023: Synthesis Report (AR6 SYR) | IPCC | 2023 | Rapport IPCC | Synthèse AR6; confirme le lien anthropique sur l’augmentation des extrêmes (chaleur, fortes précipitations) et projections à 1,5 °C.[^9] |
| 2 | State of the Global Climate 2024 | WMO | 2025 | Rapport | Confirme que 2024 est très probablement la 1ʳᵉ année complète >1,5 °C; recense de nombreux extrêmes record (chaleur, pluie, feux).[^3][^4] |
| 2 | IPCC Special Report on Climate Change and Cities (en préparation) | IPCC | ≥2025 | Rapport spécial | En cours (First Order Draft en review), pas encore de chiffres publiables; ne remplace pas AR6.[^10][^11] |


***

### PROMPT 3 — Routage WSN 2024–2026 + métaheuristiques + ACV

| Prompt | Référence | Venue | Année | Type | Contenu / Lien avec thèse |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 3A | A life cycle assessment approach to minimize environmental impact of printed hybrid sensor tags | *Scientific Reports* | 2025 | ACV capteurs | ACV ISO 14040 de tags capteurs; fournit gCO₂eq par tag mais aucun protocole de routage ACV‑aware.[^12] |
| 3A | Environmental Life‑Cycle Assessment (LCA) of Wireless RF Systems | IEEE | 2024 | ACV systèmes RF | ACV de systèmes RF, conforme ISO 14040; pas de métrique de routage.[^13] |
| 3B | Metaheuristic Approaches for Energy Optimization in WSNs: A Systematic Review | *EAI Endorsed Trans. IoT* | 2026 | SLR | SLR de 48 études (2019–2024); PSO \& ACO dominent; focus énergie/lifetime, pas carbone/ACV.[^14] |
| 3B | Energy efficient clustering and routing protocol based on quantum PSO and fuzzy logic (QPSOFL) | *Scientific Reports* | 2024 | Routage WSN | QPSO + fuzzy pour sélection CH; gains énergie, throughput, lifetime vs HHO, GWO, PSO, etc.[^15] |
| 3C | Novel Energy‑efficient Modified LEACH Routing Protocol (aerem‑LEACH) | SWCC Journal | 2024 | LEACH‑variant | Sélection CH basée sur énergie moyenne + résiduelle; meilleure durée de vie \& énergie que LEACH‑variants existants.[^16] |
| 3C | NN_ILEACH: An efficient neural network LEACH protocol | *Scientific Reports* | 2024 | LEACH‑variant | NN + EHORM; durée de vie x20 vs LEACH, +PDR/+throughput; pas de carbone/fin de vie.[^17] |

> **ACV dans routage :** aucune des références 2024–2026 ne définit un **protocole WSN** incorporant **fabrication + opération + fin de vie** dans la métrique de routage → soutient la nouveauté de CALASH.[^12][^13]

***

### PROMPT 4 — MARL pour réseaux (QMIX/QTRAN/GNN)

| Prompt | Référence | Venue | Année | Type | Point clé |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 4A | Graph Neural Network Meets Multi‑Agent Reinforcement Learning (GNNComm‑MARL) | *IEEE Comm. Surveys \& Tutorials* (prépub.) | 2024 | Survey / Framework | MARL + GNN (GAT) pour ressources \& mobilité en réseaux 6G; pas de routage WSN spécifique ni fusion QMIX+QTRAN.[^18][^19][^20] |
| 4A | Federated Model‑Based Offline Multi‑Agent RL for Wireless Networks (FedMORL) | NeurIPS | 2024 | Conférence | MARL fédéré offline pour tâches réseau; améliore throughput/délai vs heuristiques; ne combine pas QMIX+QTRAN.[^21] |
| 4B | Graph Convolutional Value Decomposition in Multi‑Agent RL (GraphMIX) | ICLR (OpenReview) | 2025 | Conférence | Factorisation de valeur via GNN; proche conceptuellement, mais ce n’est pas une fusion QMIX+QTRAN.[^22] |
| 4B | Communication using GNN in MARL (PyMARL extensions) | GitHub | 2021–2025 | Implémentation | Implémente QMIX, QTRAN, VDN, etc. avec GAT/GConv pour communication, mais pas de “policy fusion” QMIX+QTRAN; ce sont des modes distincts.[^23][^24] |

> **Fusion QMIX+QTRAN avec GNN :** aucun cadre 2024–2026 ne le fait explicitement → ton GAPF reste original sur ce point.[^23][^22][^18][^21]

***

### PROMPT 5 — Détection comprimée dynamique WSN

| Prompt | Référence | Venue | Année | Type | Contenu |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 5A/C | Redefining IoT networks for improving energy and memory efficiency | *Journal (PMC)* | 2025 | Article | Mentionne l’agrégation de données via compressive sensing ciblant des nœuds à faible mémoire; optimisation énergie/mémoire, pas carbone.[^25] |
| 5A | Energy Aware Adaptive Sampling Algorithm for EH‑WSN | Conf./Journal | 2016 | Article | Algorithme de sampling adaptatif basé sur énergie disponible + harvesting; conceptuellement proche d’une CS dynamique énergie‑aware.[^26] |

> **Carbone + CS + WSN :** rien trouvé 2024–2026 qui combine **intensité carbone du réseau + CS adaptative + routage WSN** → soutient ta revendication originale.[^25][^27][^28][^29]

***

### PROMPT 6 — ACV complète IoT/WSN (CALASH)

| Prompt | Référence | Venue | Année | Type | Rôle |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 6A | LCA printed hybrid sensor tags (ISO 14040) | *Scientific Reports* | 2025 | ACV | ACV cradle‑to‑grave pour tags capteurs; fournit gCO₂eq par device.[^12] |
| 6A | Environmental LCA of Wireless RF Systems | IEEE | 2024 | ACV | ACV de systèmes RF conformes ISO 14040.[^13] |
| 6C | Assessing the embodied carbon footprint of IoT edge devices | *J. Cleaner Production* | 2021 | ACV | Cadre paramétrique pour carbone incorporé d’objets IoT; base chiffrée utile.[^30] |

> **Protocole ACV‑aware :** aucun protocole WSN 2024–2026 ne combine ces résultats ACV dans une **métrique de routage ISO 14040** → bon support pour la nouveauté de CALASH.[^13][^30][^12]

***

### PROMPT 7 — Zéro‑confiance + AI‑native ZTA

| Prompt | Référence | Institution / Venue | Année | Type | Contenu |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 7D | ZTA‑IoT: A Novel Architecture for Zero‑Trust in IoT Systems and an Ensuing Usage Control Model | *ACM TOPS* | 2025 | Article | Architecture ZT pour IoT + score‑based authorization (ZTA‑IoT‑OL‑SAF) + modèle UCONIoT formel; pas de 5‑niveaux ni contraintes <10 ms/<2 MB.[^31][^32][^33] |
| 7D | Securing Constrained Networks through Zero Trust Architecture | Univ. Bologne (thèse) | 2024 | Thèse | Applique ZT aux réseaux contraints; discussion design, pas de bornes strictes temps/mémoire ni 5‑niveaux standardisés.[^34] |
| 7A–C | NIST SP 800‑207 Zero Trust Architecture + guides ZT | NIST, CSA, etc. | 2020–2025 | Normes / guides | Définit les principes ZT; pas de spécification <10 ms \& <2 MB sur WSN AI‑natifs.[^35][^36][^37][^38] |

> **Claim ZT (<10 ms, <2 MB, 5 niveaux, garanties formelles) :** aucun framework identifié qui coche ces 4 cases simultanément → ton cadre CASTER‑ZT reste différencié.[^31][^32][^34]

***

### PROMPT 8 — Safe RL + blindage multi‑niveaux

| Prompt | Référence | Venue | Année | Type | Contenu |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 8A | Dynamic Model Predictive Shielding (DMPS) | NeurIPS | 2024 | Article | Shielding RL avec garanties formelles de sûreté via contrôle prédictif; décision essentiellement binaire (override ou non).[^39][^40] |
| 8A | Runtime Safety through Adaptive Shielding | OpenReview | 2025 | Article | Shield adaptatif pour MDP à paramètres cachés; utilise prédiction conforme; decisions shield = autoriser/bloquer actions.[^41] |
| 8A/B | Shields for Safe Reinforcement Learning | *ACM Computing Surveys* | 2025 | Survey | Revue des méthodes de shielding (statiques, adaptatifs, hiérarchiques); toutes basées sur blocage d’actions non sûres.[^42] |

> **5‑niveaux de décision :** aucun exemple de shield avec **5 niveaux gradués + preuves formelles** trouvé → claim soutenu.[^39][^41][^42]

***

### PROMPT 9 — 6G pour catastrophes (sub‑THz, RIS, ISAC, O‑RAN)

| Prompt | Référence | Venue | Année | Contenu |
| :-- | :-- | :-- | :-- | :-- |
| 9B/D | Fast Network Recovery from Large‑Scale Disasters | arXiv | 2024 | Open6GRAN 6G RAN résilient (RIS, cell‑free, NTN) pour recovery rapide; RAN contrôleur IA.[^43] |
| 9B/C | Optimizing disaster response with UAV‑mounted RIS and HAP edge | *Computer Networks* | 2025 | UAV + HAP + RIS pour PPDR; optimisation conjointe placement/configuration/power.[^44] |
| 9B/C | Next‑generation wireless communication technologies for disaster response | *ETRI Journal* | 2024 | Revue des technos sub‑THz, NTN, RIS, ISAC pour secours.[^45] |
| 9B | Communications and Networking for Public Safety | IEEE PST | 2025 | Livre blanc sur réseaux 5G/6G PPDR (UAV, NTN, RIS, O‑RAN) et exigences latence/fiabilité.[^46] |


***

### PROMPT 10 — DRL pour routage / gestion de réseaux

| Prompt | Référence | Venue | Année | Contenu |
| :-- | :-- | :-- | :-- | :-- |
| 10A–C | GNNComm‑MARL | *IEEE Comm. Surveys \& Tutorials* (prépub.) | 2024 | Marche à suivre MARL+GNN pour ressources/mobilité; pas de routage WSN léger sur MCU.[^18][^19] |
| 10A–C | FedMORL | NeurIPS | 2024 | FL + offline MARL pour réseaux sans fil; pas de stats PDR/énergie pour WSN ni comparaison QMIX/QTRAN.[^21] |


***

### PROMPT 11 — Intensité carbone + outils temps réel (grids)

| Prompt | Référence | Institution | Année | Contenu |
| :-- | :-- | :-- | :-- | :-- |
| 11A | API Based | SCI Guidance – Green Software Foundation | 2024–2025 | Décrit comment utiliser Electricity Maps, WattTime, etc., et le Carbon Aware SDK pour scheduler des charges selon l’intensité carbone.[^27] |
| 11A | Electricity Maps platform updates | Electricity Maps | 2026 | Confirme que la plateforme fournit mix, prix, intensité carbone en temps réel, historique, prévisionnel.[^28] |
| 11A/B | Carbon Intensity Level API | Green Web Foundation + Electricity Maps | 2026 | API de niveau d’intensité (low/moderate/high) basée sur moyenne mouvante 10 jours; application à des sites “grid‑aware”.[^47] |
| 11B | Framework for Comparison of Carbon Intensity Signals | ACM | 2025 | Compare signaux carbone (moyenne vs marginal, etc.) pour load shifting; utile pour justifier le choix de signal.[^29] |


***

### PROMPT 12 — IA générative + sécurité + ZT

Pas de papier unique qui formalise **ZT + guardrails LLM + garanties formelles** pour systèmes autonomes; tu peux t’appuyer sur :

- **NIST AI RMF** (gestion de risques IA).
- **OWASP Top 10 for LLM Applications** (2024) pour menaces et mitigations.
- Documents industriels (Anthropic *Constitutional AI*, OpenAI *Model spec*, Google *Gemini safety*) pour l’état de l’art des guardrails.

***

### PROMPT 13 — Paradigmes WSN intelligents (FL, jumeaux numériques, sémantique)

Les résultats 2024–2026 sont surtout :

- FL pour IoT/IIoT (par ex. FL asynchrone pour intrusion detection IIoT 2024), mais rien de très ciblé WSN catastrophes.[^48]
- Digital twins pour 5G/6G et O‑RAN (dans des surveys 6G), pas en WSN pur.
- Semantic comms pour 6G/IoT (hors WSN catastrophes).

→ Tu peux présenter ces thèmes comme **axes émergents, peu matérialisés pour WSN catastrophes**.

***

### PROMPT 14 — GNN dynamiques + MARL

| Prompt | Référence | Venue | Année | Contenu |
| :-- | :-- | :-- | :-- | :-- |
| 14A/B | A Comprehensive Survey of Dynamic Graph Neural Networks | *IEEE TKDE* | 2026 | Survey sur GNN dynamiques (TGN, TGAT, etc.), scalabilité, inductifs, benchmarks.[^49] |
| 14C | Graph Neural Network Meets Multi‑Agent RL | *IEEE Comm. Surveys \& Tutorials* | 2024 | Voir ci‑dessus; explore GNN+MARL pour réseaux 6G.[^18][^20] |


***

### PROMPT 15 — TinyML embarqué + inference MCU

| Prompt | Référence | Venue | Année | Contenu |
| :-- | :-- | :-- | :-- | :-- |
| 15A–C | Deploying TinyML for energy-efficient object detection and monitoring on ARM microcontrollers | *Scientific Reports* | 2025 | Déploiement TinyML sur MCU ARM; quantization/pruning, mesures de RAM/latence.[^50] |
| 15A | From Models to Microcontrollers: TinyML Tools, Techniques and Strategies | Rapport DTU | ≈2024–2025 | Revue de 12 frameworks TinyML, options de quantification, pipelines MCU.[^51] |
| 15A | A Review on the emerging technology of TinyML | *ACM* | 2024 | Survey sur TinyML, modèles compacts, sécurité, edge AI.[^52] |


***

Si tu veux, je peux maintenant te générer un **fichier CSV** avec toutes ces lignes (une par entrée) que tu pourras importer dans Excel/Overleaf; dis‑moi juste si tu préfères un CSV anglais ou français pour les noms de colonnes.
<span style="display:none">[^53][^54][^55][^56][^57][^58][^59][^60][^61][^62][^63][^64]</span>

<div align="center">⁂</div>

[^1]: https://files.emdat.be/2025/05/CredCrunch78.pdf

[^2]: https://www.preventionweb.net/publication/2024-disasters-numbers

[^3]: https://wmo.int/publication-series/state-of-global-climate/state-of-global-climate-2024

[^4]: https://www.ecowatch.com/extreme-climate-events-2024-wmo.html

[^5]: https://www.swissre.com/institute/research/sigma-research/sigma-2025-01-natural-catastrophes-trend.html

[^6]: https://www.artemis.bm/news/munich-re-estimates-2024-insured-catastrophe-losses-at-140bn/

[^7]: https://www.munichre.com/en/risks/natural-disasters.html

[^8]: https://www.munichre.com/content/dam/munichre/mrwebsitespressreleases/MunichRe-NatCAT-Stats2024-Full-Year-Factsheet.pdf/_jcr_content/renditions/original./MunichRe-NatCAT-Stats2024-Full-Year-Factsheet.pdf

[^9]: https://www.ipcc.ch/report/ar6/syr/

[^10]: https://www.ipcc.ch/report/special-report-on-climate-change-and-cities/

[^11]: https://www.gov.uk/government/publications/ipcc-special-report-on-climate-change-and-cities-expert-review

[^12]: https://www.nature.com/articles/s41598-025-95682-8

[^13]: https://ieeexplore.ieee.org/iel8/9171629/10803549/10703165.pdf

[^14]: https://publications.eai.eu/index.php/IoT/article/view/10328

[^15]: https://www.nature.com/articles/s41598-024-69360-0

[^16]: https://www.benthamdirect.com/content/journals/swcc/10.2174/0122103279296700240430095450

[^17]: https://www.nature.com/articles/s41598-024-75904-1

[^18]: https://arxiv.org/abs/2404.04898

[^19]: https://www.themoonlight.io/en/review/graph-neural-network-meets-multi-agent-reinforcement-learning-fundamentals-applications-and-future-directions

[^20]: https://arxiv.org/html/2404.04898v1

[^21]: https://neurips.cc/virtual/2025/123189

[^22]: https://openreview.net/forum?id=gDikr8MVsMF

[^23]: https://cops-iitbhu.github.io/IG-website/gnn_marl

[^24]: https://github.com/hex-plex/GNN-MARL

[^25]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12297550/

[^26]: https://www.research-collection.ethz.ch/entities/publication/e60d1dd8-661e-46b7-a534-f3336023a43b

[^27]: https://sci-guide.greensoftware.foundation/I/APIBased/

[^28]: https://www.electricitymaps.com/resources/updates

[^29]: https://dl.acm.org/doi/10.1145/3679240.3734597

[^30]: https://www.sciencedirect.com/science/article/abs/pii/S0959652621031577

[^31]: https://dl.acm.org/doi/pdf/10.1145/3671147

[^32]: https://dl.acm.org/doi/10.1145/3671147

[^33]: https://www.linkedin.com/posts/safwa-ameer_zta-iot-a-novel-architecture-for-zero-trust-activity-7211006176036106242-ksrN

[^34]: https://amslaurea.unibo.it/id/eprint/34639/1/Securing_Constrained_Networks_through_Zero_Trust_Architecture.pdf

[^35]: https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-207.pdf

[^36]: https://csrc.nist.gov/pubs/sp/800/207/final

[^37]: https://www.cyber.gc.ca/en/guidance/zero-trust-approach-security-architecture-itsm10008

[^38]: https://cloudsecurityalliance.org/artifacts/zero-trust-guidance-for-iot

[^39]: https://openreview.net/forum?id=x2zY4hZcmg

[^40]: https://neurips.cc/virtual/2024/poster/93108

[^41]: https://openreview.net/forum?id=tIa69ILtVq

[^42]: https://dl.acm.org/doi/10.1145/3715958

[^43]: https://arxiv.org/abs/2408.08609

[^44]: https://www.sciencedirect.com/science/article/abs/pii/S1084804525001109

[^45]: https://onlinelibrary.wiley.com/doi/10.4218/etrij.2024-0546

[^46]: https://publicsafety.ieee.org/wp-content/uploads/2025/05/PST-Comms-Networking-White-Paper_Final_April2025-2.pdf

[^47]: https://www.thegreenwebfoundation.org/news/a-new-api-for-grid-aware-websites-and-beyond/

[^48]: https://cerc-ngct.ca/publications-3/

[^49]: https://www.computer.org/csdl/journal/tk/2026/01/11202740/2aOjweMbtWo

[^50]: https://www.nature.com/articles/s41598-025-27818-9

[^51]: https://orbit.dtu.dk/files/440425747/From_Models_to_Microcontrollers_-_TinyML_Tools_Techniques_and_Strategies.pdf

[^52]: https://dl.acm.org/doi/10.1145/3661820

[^53]: https://www.iso.org/standard/37456.html

[^54]: https://di-engine-docs.readthedocs.io/en/latest/12_policies/qtran.html

[^55]: https://www.lifecycleinitiative.org/wp-content/uploads/2012/12/SLCA and LCSA.pdf

[^56]: https://proceedings.mlr.press/v97/son19a.html

[^57]: https://www.cisco.com/c/dam/en_us/about/csr/environmental-sustainability/dp-9871-iso-aligned-lca-report.pdf

[^58]: https://acta.uni-obuda.hu/LKiss_TothneSzitaPinterKosaVeres_148.pdf

[^59]: https://arcticdomainawarenesscenter.org/Downloads/StudentWork/Graduate Thesis_Matthew%20Ahlrichs_2018.pdf

[^60]: https://espace.etsmtl.ca/id/eprint/3528/1/SOLTANZADEH_Amirmasoud.pdf

[^61]: https://arxiv.org/html/2601.04177v1

[^62]: https://hal.univ-grenoble-alpes.fr/hal-00657514/

[^63]: https://arxiv.org/pdf/1905.05408.pdf

[^64]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8623548/


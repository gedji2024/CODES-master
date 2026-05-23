# PhD Defense — Speaker Notes
**Georges Parfait Djimefo Kapen — Polytechnique Montréal — July 2026**
**Total time: 30 minutes | ~25 slides | ~1 min/slide average**

---

## PACING GUIDE

| Section | Slides | Time |
|---------|--------|------|
| Title + Outline | 2 | 1 min |
| Context & Motivation | 2 | 3 min |
| Problem & Objectives | 2 | 3 min |
| Methodology | 2 | 2 min |
| Article 1 — GAPF | 3 | 5 min |
| Article 2 — CALASH | 3 | 5 min |
| Article 3 — CASTER-ZT | 2 | 4 min |
| Discussion & Summary | 3 | 4 min |
| Contributions & Impact | 2 | 2 min |
| Limitations & Future work | 2 | 1 min |
| Conclusion | 1 | 1 min |
| Thank you | — | 30 s |

---

## SLIDE 1 — Title

> *Stand in silence for 3 seconds. Make eye contact with the jury before speaking.*

"Good morning. My name is Georges Parfait Djimefo Kapen. Today I am defending my PhD thesis entitled: *AI-Driven Intelligent Routing and Secure Autonomous Recovery in 6G-Integrated Disaster-Monitoring Sensor Networks.*

This work was conducted under the supervision of Professor Ranwa Al Mallah and co-supervisor Professor Samuel Pierre, in the LARIM laboratory at Polytechnique Montréal.

In the next 30 minutes, I will show you why sensor networks that monitor natural disasters need to be more efficient, greener, and safer — and how I built a complete solution to achieve exactly that."

---

## SLIDE 2 — Outline

> *Brief. Just orient the audience.*

"Here is the roadmap for today. I will start with the context — why this research matters. Then I will walk you through three articles, each solving one major challenge. I will close with a discussion of results, limitations, and what comes next."

---

## SLIDE 3 — Context: Natural Disasters and Monitoring

> *This slide speaks to everyone — technical or not. Take your time.*

"Let's start with a number that should concern all of us. Between 2000 and 2019, there were over 7,000 major natural disasters worldwide — earthquakes, floods, hurricanes. That's 4.2 billion people affected, 1.2 million deaths, and nearly 3 trillion dollars in economic losses.

In 2023 alone: 398 disasters, 95,000 deaths. And climate change is making it worse — scientists project 30% more frequent extreme weather events in the coming decades.

The Sendai Framework, adopted by 187 countries in 2015, sets a clear goal: strengthen early warning systems so that people can evacuate before disaster strikes.

The question is: *how do you monitor a disaster zone in real time?* The answer is: with wireless sensor networks — small, cheap, autonomous devices scattered across an area that continuously send data. That is what this thesis is about."

---

## SLIDE 4 — WSNs: Potential and Constraints

> *Brief contrast. Set up the engineering tension.*

"Sensor networks are powerful — they can cover large areas autonomously, they're cheap, and they work even after a disaster hits. But they have severe constraints.

Think of a sensor as a small coin-battery-powered device: about half a joule of energy total. They can't be recharged. They have very limited memory. And they're physically exposed to the very disaster they're monitoring.

On top of that, we are now entering the era of 6G — the next generation of mobile communications, with terahertz frequencies, intelligent reflective surfaces, and ultra-low latency. This opens new possibilities for sensor networks — but also new complexities to manage.

So we have a challenging environment. Let me now tell you what exactly needs to be solved."

---

## SLIDE 5 — Three Fundamental Challenges

> *Three problems, three articles. Announce the structure clearly.*

"This thesis identifies three fundamental challenges that no existing approach has solved simultaneously.

**Challenge 1 — Energy.** Routing — deciding how each sensor forwards its data — is the number one factor in how long a sensor network lives. Existing AI-based methods require tens of thousands of parameters per sensor agent. They are simply too heavy for embedded devices, and none of them intelligently combines multiple strategies based on the network topology.

**Challenge 2 — Carbon.** Most people think about energy consumption. But actually, the biggest carbon footprint of a sensor comes from *manufacturing it* — not running it. The embedded carbon from production is a million times larger than what the sensor consumes per packet. No existing routing protocol accounts for this full lifecycle carbon. None.

**Challenge 3 — Security.** When you put AI in the control loop, you create a new attack surface. A sensor can be compromised. The AI policy can be manipulated. Existing defenses are binary — they either allow or block. But in a disaster zone, blocking everything is not an option. You need nuance.

These three challenges — efficiency, sustainability, security — are what this thesis solves."

---

## SLIDE 6 — Research Questions and Objectives

> *Read the main question clearly and slowly. It is the anchor of the thesis.*

"The main research question that guides this thesis is:

*'How do you design a complete intelligent routing protocol stack — energy-efficient, carbon-sustainable, and secure — for AI-native sensor networks integrated with 6G?'*

I translated this into three specific questions and three specific objectives — one per article. I will not read all of them now, but I want you to notice that each objective has a measurable target: packet delivery ratio above 98%, carbon reduction of 33%, zero false positives in security, all within the 10 millisecond real-time budget of the 6G standard."

---

## SLIDE 7 — Methodological Approach

> *Keep it brief — the jury already knows DSR.*

"Methodologically, this work follows the Design Science Research framework — a rigorous approach for research that produces concrete artifacts, in this case three software frameworks.

The three articles follow a deliberate progression: GAPF is the foundation — it solves efficiency. CALASH extends the work to sustainability. CASTER-ZT adds the protection layer. But notice the feedback arrow — the security layer also protects the gains achieved by the two earlier layers. This is not three independent papers. This is one integrated stack."

---

## SLIDE 8 — Common Experimental Protocol

> *Establish credibility fast.*

"All three articles share a common evaluation philosophy: simulations anchored in real-world data. We used real sensor traces from the Intel Berkeley Lab, real carbon intensity data from the UK grid API, and real seismic models calibrated on the 2023 Turkey-Syria earthquake — magnitude 7.8.

In total, across the three articles, we ran more than 23,800 simulations. All results report 95% confidence intervals. This is not a small study."

---

## SLIDE 9 — GAPF: Architecture

> *First article. Spend time on the diagram — it's the core idea.*

"Let me introduce the first article: GAPF — Graph-Attentive Policy Fusion.

The core idea is simple but powerful. Instead of training one large neural network to control routing — which would be too heavy for sensors — I took two existing AI agents that were already trained, QMIX and QTRAN, froze their weights, and built a lightweight meta-controller on top.

This meta-controller — shown here — does two things. The GCN, or Graph Convolutional Network, reads the topology of the sensor network and produces a compact summary of the current state. Then the CAS — the Contextual Algorithm Selector — uses that summary to decide *which expert to trust* in the current moment.

Think of it like a coach who watches two specialists. One specialist is great at coordinating closely-packed teams. The other is better at handling more spread-out formations. The coach watches the field and decides who to listen to. That is GAPF.

The whole meta-controller has only 1,473 trainable parameters. For comparison, a single traditional MARL agent has 39,000 parameters. We are 26 times lighter."

---

## SLIDE 10 — GAPF: Why Fusion Works

> *This is the scientific justification — keep it accessible.*

"Why does fusion work? Because QMIX and QTRAN are complementary. QMIX is very good at tight coordination — it guarantees that improving one agent always improves the team. QTRAN handles more complex, non-monotonic interactions. They make different mistakes in different situations. By combining them contextually, we get the best of both.

We also introduced a novel component: the monotonic attention network, which scalarizes the multi-objective reward — energy, delivery rate, latency — in a way that is mathematically guaranteed never to rank a worse solution higher than a better one. This is a formal property called Pareto monotonicity, which existing methods do not guarantee."

---

## SLIDE 11 — GAPF: Key Results

> *Numbers — state them clearly and with confidence.*

"The results speak for themselves. Compared to the best existing method, QMIX:

- Packet delivery rate went from 46–67% up to **98% and above** — an improvement of 43 to 111%.
- Energy consumption dropped to **less than half** — 2 to 3.5 times lower.
- The model fits in **5.8 kilobytes** — directly deployable on a 10-dollar ARM microcontroller, no compression needed.
- Training memory dropped from up to 14 gigabytes to under 1 gigabyte.

This was validated on 21,000 simulation episodes across 7 different network scenarios ranging from 20 to 100 sensors."

---

## SLIDE 12 — CALASH: Architecture

> *Second article. Explain the lifecycle insight clearly — it's counterintuitive.*

"The second article is CALASH — Carbon-Aware Lifecycle Autonomous Self-Healing.

Before I explain the architecture, let me share the key insight that motivated it. When you think about the carbon footprint of a sensor, you probably think about the electricity it uses. But the manufacturing of the sensor — the silicon, the battery, the casing — costs one million times more carbon per packet than the electricity consumed during operation. The only way to amortize that embedded carbon is to maximize the number of *useful packets* the sensor delivers over its lifetime.

This is the fundamental principle: the greener routing strategy is the one that keeps the network alive longer and delivers more data efficiently.

CALASH implements this through four pillars, each handling one part of the lifecycle:

- **CADR** adapts how much data is compressed based on how dirty the electrical grid is right now.
- **CARE** makes routing decisions using a hybrid Lyapunov optimization with a virtual carbon queue — a mathematical mechanism that enforces a long-term carbon budget.
- **SHDR** is the self-healing component — it monitors the network, detects dead nodes after a disaster, and automatically rebuilds the topology.
- **LSE** tracks the full lifecycle carbon using a metric we call LCI — Lifecycle Carbon Intensity — expressed in grams of CO2 per useful packet delivered, compliant with the ISO 14040 standard.

All of this runs over a 6G dual-band physical layer — using both sub-terahertz for high throughput and traditional sub-6 GHz for coverage, with intelligent reflecting surfaces."

---

## SLIDE 13 — CALASH: Four Pillars

> *Optional deeper dive — can skim if short on time.*

"To summarize the four pillars briefly: CADR is the data reduction layer — compress more when the grid is dirty, less when it's clean. CARE is the routing brain — it uses Lyapunov mathematics to prove that it simultaneously converges toward maximum delivery AND stays within a carbon budget. SHDR is the resilience layer — MAPE-K autonomic loop that rebuilds the network after damage. And LSE is the accounting layer — it tracks the full environmental cost of every decision."

---

## SLIDE 14 — CALASH: Key Results

> *Again, numbers with confidence.*

"CALASH results, compared to LEACH — the standard baseline:

- Network lifetime: from 931 rounds to **1,486 rounds** — **60% longer**.
- Packet delivery ratio: **82.9%** — high even in harsh disaster conditions.
- Carbon footprint per packet: from 13.42 down to **8.99 grams of CO2 equivalent** — a **33% reduction**.

This was validated on 390 runs with 30 independent Monte Carlo seeds, using real carbon intensity data from four different national grids — France, Germany, Poland, Norway — showing the gains are robust regardless of the energy mix."

---

## SLIDE 15 — CASTER-ZT: Architecture

> *Third article. Lead with the threat, then the solution.*

"The third article is CASTER-ZT — and it addresses a problem that is rarely discussed in sensor network research: what happens when the AI itself is compromised?

When you put AI in the control loop of a disaster-monitoring network, you are trusting that AI to make the right routing decisions. But what if a sensor node has been hacked and is broadcasting false information? What if the AI policy — trained to recover from failures — has been manipulated to route packets into the void?

Existing solutions are binary: allow or block. But in a critical mission, blocking every suspicious decision shuts down the network. You need graduated responses.

CASTER-ZT introduces a zero-trust decision shield — inspired by the NIST SP 800-207 standard. Every decision proposed by the AI goes through a verification pipeline. The GraphSAGE encoder reads the network topology. The policy head proposes an action. Then four evaluators assess: Is the source trustworthy? Is this action risky? Does it diverge from normal behavior? Is the actor even authorized to act?

The zero-trust shield then issues one of five graduated decisions — shown at the bottom: Allow, Scope-reduce, Defer, Escalate, or Block.

Crucially, the shield itself is **deterministic** — 14 scalar parameters, no learning. It cannot be fooled by adversarial examples because it does not rely on neural network outputs to make its final decision."

---

## SLIDE 16 — CASTER-ZT: Results

> *Zero false positives is the headline — emphasize it.*

"CASTER-ZT results:

- Rogue policy detection: **74 to 98%** depending on attack type.
- False positives: **zero percent** — the shield never incorrectly blocks a legitimate action. Never. This is formally guaranteed, not just empirically observed.
- Recovery score: 0.733 — 3.7 to 5.2 times better than existing methods.
- Decision latency: **3.07 milliseconds** — well within the 10ms real-time budget mandated by the O-RAN standard for 6G control loops.

This was validated on 2,420 simulation runs, tested against four attack scenarios including coordinated rogue policies and out-of-distribution hallucinations."

---

## SLIDE 17 — Protocol Stack Synergies

> *This is the thesis's key insight beyond the three individual contributions.*

"Now let me take a step back and explain why these three frameworks form a *stack* rather than three separate papers.

The synergies are real and directional:

- GAPF delivers data efficiently — which directly reduces operational carbon. More efficient routing means less energy per packet, which means lower CO2.
- CALASH reduces data volume through compression — which reduces the number of transmissions — which reduces the attack surface that CASTER-ZT needs to monitor.
- CASTER-ZT protects the entire stack — if it didn't exist, a single compromised node could invalidate all the efficiency and sustainability gains of GAPF and CALASH.

The whole stack costs approximately 27,000 trainable parameters — comparable to a single traditional MARL agent. We achieve efficiency, sustainability, AND security at the cost of a single baseline algorithm."

---

## SLIDE 18 — Overall Quantitative Summary

> *The jury will look at this table carefully. Walk through it row by row.*

"Let me give you the complete quantitative picture. This table summarizes all gains across the three articles compared to the best existing baselines:

- Packet delivery: from 46–67% up to 98%. Improvement of 43 to 111%.
- Energy: 2 to 3.5 times lower per packet.
- Parameters: 26 times fewer — 1,473 versus 39,000.
- Network lifetime: 60% longer.
- Carbon footprint: 33% lower.
- Security: 74 to 98% detection with zero false positives — the previous best had 48.8% false positives.
- Decision latency: 3.3 times faster than the O-RAN budget.
- Coverage of the 12 gap criteria identified in the literature review: 12 out of 12.

No existing approach covers more than 1 of those 12 criteria. We cover all 12."

---

## SLIDE 19 — TinyML Deployability

> *This slide shows practical impact — make it tangible.*

"One of the most important practical results of this thesis is deployability. The complete protocol stack — all three frameworks combined — requires 27,000 parameters and fits in 103 kilobytes. That's less than a small image file.

For context: MCUNet, the current state of the art for deploying deep learning on microcontrollers, deploys about 1 million parameters. Our stack is **38 times lighter**.

This means the complete AI system can run on microcontrollers that cost a few dollars. This is crucial — 95% of disaster deaths occur in developing countries. A solution that requires expensive hardware helps no one. A solution deployable on a $5 chip can save lives."

---

## SLIDE 20 — Six Original Scientific Contributions

> *Read each contribution with one sentence of context.*

"Let me now enumerate the six original contributions of this thesis:

**C1** — The first framework that uses a graph neural network to fuse multiple MARL policies for routing in sensor networks. The GNN+CAS paradigm is transferable to any multi-agent system.

**C2** — The first monotonic attention network for multi-objective reward scalarization in routing. Pareto monotonicity is formally guaranteed — a property absent from all existing scalarization methods.

**C3** — The first Lifecycle Carbon Intensity metric for sensor networks, compliant with ISO 14040. This metric can be adopted as a standard benchmark for any IoT protocol evaluation.

**C4** — The first four-pillar routing protocol with mathematical Lyapunov guarantees on both delivery rate and carbon budget simultaneously.

**C5** — The first zero-trust decision control framework for AI-native networks, with five graduated decisions, ten formal propositions, and a deterministic explainable shield.

**C6** — A demonstration that energy efficiency, carbon sustainability, and security are not trade-offs. They reinforce each other. This is a systemic result."

---

## SLIDE 21 — Impact and SDG Alignment

> *Brief — connect to real-world stakeholders.*

"These contributions have concrete implications across three stakeholder groups.

For **industry**: the 5.8 KB GAPF model eliminates the need for costly edge gateways. The 60% lifetime improvement reduces maintenance costs. The LCI metric provides a standardized tool for sustainability reporting under CSRD regulations. The auditable shield simplifies IEC 62443 certification.

For **governments**: the LCI offers a standardized IoT indicator that regulators can mandate. GAPF and CALASH contribute directly to two Sendai Framework indicators — C-2 and C-6 — which measure early warning coverage. All algorithms are open-access, no vendor dependency.

For **society** and the United Nations SDGs: we contribute to SDG 9 (resilient infrastructure), SDG 11 (reduce disaster deaths), SDG 12 (sustainable production), SDG 13 (climate action), and SDG 16 (transparent institutions)."

---

## SLIDE 22 — Acknowledged Limitations

> *Be direct and confident. Knowing your limits shows scientific maturity.*

"I want to be transparent about the limitations of this work.

Methodologically: all results are simulation-based. We used real-world data for calibration, but we have not yet validated on physical hardware. The disaster model uses a Gaussian spatial distribution — adequate for earthquakes, but not for slow-moving floods or wildfires. The 6G physical layer uses analytical models, not full 3D ray tracing.

Technically: the three frameworks have not been integrated and tested as a unified system. Their performance beyond 200 nodes is not characterized. The security model assumes static adversaries — adaptive attackers who learn to evade the shield are not covered. And we have not conducted user studies with emergency responders.

These are honest limitations. They define exactly what the next phase of this research must address."

---

## SLIDE 23 — Future Research Directions

> *Forward-looking and energetic. This is the opening, not the closing.*

"The roadmap ahead is clear.

In the **short term** — one to two years — the priority is integration: combining the three layers into one system and testing on real hardware like the Zolertia RE-Mote or NVIDIA Jetson. We also need more realistic disaster models.

In the **medium term** — two to four years — federated learning allows training without centralizing sensitive data. Digital twins provide a continuous simulation environment for policy updates before deployment. Formal verification using theorem provers like Coq would allow certification of the shield for safety-critical systems.

In the **long term** — four-plus years — we are looking at non-terrestrial networks: LEO satellites, high-altitude platforms, drones as mobile base stations after a disaster. We are also looking at standardization — submitting the LCI metric and the zero-trust framework to ISO, ETSI, and 3GPP.

And beyond disaster monitoring — the same principles apply to precision agriculture, smart cities, connected healthcare, and drone swarms."

---

## SLIDE 24 — Conclusion

> *This is the moment. Calm, clear, confident.*

"To conclude.

This thesis proposed a complete protocol stack for intelligent routing in 6G-integrated disaster-monitoring sensor networks, built around three complementary frameworks.

GAPF solves the energy problem: 1,473 parameters, packet delivery above 98%, energy consumption cut by 2 to 3.5 times.

CALASH solves the carbon problem: four pillars, Lyapunov guarantees, 33% carbon reduction, 60% longer network lifetime.

CASTER-ZT solves the security problem: five graduated decisions, zero false positives, 10 formal propositions, 3.07 milliseconds per decision.

The central message of this thesis is this: AI, designed with *parsimony*, *environmental awareness*, and *systematic verification*, is a reliable tool for critical environments.

We don't need bigger models. We need *smarter* ones."

---

## SLIDE 25 — Thank You / Questions

> *Stop. Take a breath. Smile. Let the silence do the work.*

"Thank you for your attention.

I am ready for your questions."

---

## BACKUP SLIDES — Quick Reference

### Backup 1 — Convergence and Theoretical Guarantees
- **GAPF**: QMIX converges within monotonic functions (IGM constraint). QTRAN covers a larger space via affine factorization. CAS acts as a variance reducer (analogous to Wolpert's stacking).
- **CALASH**: Lyapunov drift-plus-penalty. Converges to within O(1/V) of the optimum. V=100 gives -33% LCI with acceptable latency. CDL bound proves *simultaneous* convergence on both PDR and carbon budget.
- **CASTER-ZT**: 10 propositions proved by logical construction. Monotone conservatism, unauthorized-actuation exclusion, conformal calibration coverage, bounded security price.

### Backup 2 — Gap Analysis (12 criteria)
No existing approach covered more than 1 of 12 identified criteria. Our stack covers all 12. Criteria include: energy-efficient routing, topology awareness, MARL fusion, Pareto scalarization, lifecycle carbon metric, carbon-aware compression, carbon budget guarantees, self-healing, 6G PHY, rogue detection, graduated decisions, formal security proofs.

### Backup 3 — Dec-POMDP Complexity
Optimal Dec-POMDP is NEXP-complete. CTDE (QMIX, QTRAN) is a structured approximation that reduces joint action space from |A|^n to Σ|A_i|. GAPF adds a meta-level of expert selection. The 98% PDR result is not a proof of global optimality — it is a high-quality approximation validated empirically over 21,000 episodes.

---

## FREQUENTLY EXPECTED JURY QUESTIONS

**Q: Why not train a single end-to-end policy instead of fusing QMIX and QTRAN?**
> "Training a single monolithic policy requires the training infrastructure to scale with n agents — 39K parameters each. GAPF exploits the complementarity of two already-proven specialists and adds only 1,473 parameters on top. The portfolio paradigm is well-established in combinatorial optimization. The 26× parameter reduction and the formal Pareto monotonicity guarantee are arguments for this approach over a monolithic one."

**Q: The simulation uses a Gaussian disaster model — how realistic is that?**
> "The Gaussian model captures the spatial decay of impact from a seismic epicenter. It was calibrated on real ShakeMap data from the Turkey-Syria 2023 earthquake. For slow-moving disasters like floods or wildfires, a different model would be needed — that is explicitly acknowledged as a limitation and motivates the extended disaster model work planned for year 1 of the future research agenda."

**Q: How do you justify the 6G assumption for sensor networks?**
> "The 6G integration is through the O-RAN architecture — the sensors do not run 6G themselves. The cluster heads communicate with the base station via a 6G dual-band link. This is realistic given the 2030 deployment horizon for 6G, which aligns with when disaster-monitoring systems built today would be in operation."

**Q: CASTER-ZT says zero false positives — is that a guarantee or an empirical result?**
> "Both. The zero false positive rate is a formal consequence of the shield's correctness property (Proposition 1): the shield only blocks when the composite conservatism score exceeds a calibrated threshold. A legitimate action by definition has low risk and high trust — it will never cross that threshold. The 0% is then confirmed empirically across 2,420 runs."

**Q: How does the LCI metric compare with existing environmental metrics in IoT?**
> "Existing metrics measure energy per packet (Joules/packet) or operational lifetime. They ignore embodied carbon — the carbon emitted during manufacturing. The LCI metric we define integrates manufacturing, operational, and end-of-life carbon into a single value in gCO2eq per useful packet, following ISO 14040. It is the first metric of this kind for WSN routing protocols. Its adoption as a standard benchmark is a key recommendation to the research community."

**Q: Why was there no hardware deployment?**
> "Hardware deployment is the next step — it is the first item in the short-term research agenda. The decision to complete simulation evaluation first was deliberate: we needed to validate the algorithms across a large parameter space (21,000 episodes, 7 scenarios) that would be infeasible on physical hardware. The feasibility analysis (Annex E) shows theoretical compatibility with Cortex-M4 at under 1ms inference latency — making the hardware step a validation, not an exploration."

---

*Good luck. You've done the work. Trust it.*

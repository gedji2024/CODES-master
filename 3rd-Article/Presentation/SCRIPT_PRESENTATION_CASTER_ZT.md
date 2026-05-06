# SCRIPT DE PRÉSENTATION — CASTER-ZT (VERSION RÉVISÉE)
**Durée totale : 20 minutes strictes (~1 180 mots / 120 mots par minute)**
**Langue : Français**
**Audience : mixte (sécurité, IA, réglementation, non-technique)**

> 📌 **Conventions :**
> - `[PAUSE]` = silence de 1-2 secondes, laisser l'idée atterrir.
> - `[GESTE]` = suggestion de geste vers la diapositive.
> - `⚠️ [ANALOGIE]` = comparaison pédagogique, pas dans l'article — à identifier comme telle si un jury pose la question.
> - Chaque bloc indique le **nombre de mots** et la **durée à 120 mots/min** pour respecter le timing.

> 📌 **Conventions :**
> - `[PAUSE]` = silence de 1-2 secondes.
> - `[GESTE]` = geste vers la diapositive.
> - `⚠️ [ANALOGIE]` = comparaison pédagogique personnelle, **pas dans l'article**.
> - Chaque diapositive indique le nombre de mots et la durée estimée.
> - **Source identifiée** : `[article]` = dans le papier soumis, `[slides]` = dans la présentation.

---

## DIAPOSITIVE 1 — Titre
**~60 mots — ⏱ 30 secondes**
*Source : [slides]*

Bonjour à tous.

Je m'appelle Georges Parfait Djimefo Kapen, doctorant à Polytechnique Montréal, sous la direction des professeurs Ranwa Al Mallah et Samuel Pierre.

Aujourd'hui je vous présente CASTER-ZT — un système qui permet à une intelligence artificielle de réparer un réseau de communication en crise, **sans qu'un attaquant puisse en prendre le contrôle**.

`[PAUSE]`

---

## DIAPOSITIVE 2 — Plan
**~55 mots — ⏱ 30 secondes**
*Source : [slides]*

En vingt minutes, nous allons voir :

Le **contexte** — pourquoi ce problème existe et pourquoi il est urgent.
Les **travaux existants** et ce qui leur manque.
Notre **système** et comment il fonctionne — en langage simple.
Les **résultats** concrets avec ce qu'ils signifient.
Et les **limites honnêtes** de notre approche.

---

## DIAPOSITIVE 3 — Contexte : Le défi de la récupération autonome
**~170 mots — ⏱ 1 min 25 sec**
*Source : [article §I, §III-B, slides]*

Imaginez une catastrophe naturelle — un séisme, une inondation.

Les antennes de téléphonie — que nous appelons **cellules** — tombent en panne massivement. Dans nos expériences, basées sur des données réelles de terrain, **environ 40 % des cellules peuvent tomber simultanément.** `[article §III-B]`

`[PAUSE]`

Pendant une catastrophe, les secouristes ont besoin du réseau pour se coordonner. Chaque seconde compte.

Or, les standards internationaux de la 6G — l'O-RAN Near-RT RIC — imposent une réaction en **moins de 10 millisecondes**. `[article §I]` Un opérateur humain ne peut pas réagir aussi vite. La solution naturelle est donc de confier la récupération à une **IA autonome**.

`[PAUSE]`

Mais voilà le problème, que nous appelons le **dilemme de l'autonomie** :

La même autonomie qui accélère la réparation **agrandit aussi la surface d'attaque**. `[article §I]`

Un attaquant peut envoyer de fausses données de capteurs pour tromper l'IA. Ou voler des identifiants légitimes pour injecter des commandes malveillantes qui ressemblent à des commandes de réparation normales.

`[PAUSE]`

C'est exactement ce problème que CASTER-ZT cherche à résoudre.

---

## DIAPOSITIVE 4 — Contexte : Le manque de sécurité
**~150 mots — ⏱ 1 min 15 sec**
*Source : [article §I–II, slides]*

Trois types d'attaques sont modélisés dans notre article. `[article §III-B]`

**Empoisonnement de télémétrie :** l'attaquant falsifie les lectures des capteurs. L'IA prend de mauvaises décisions en toute bonne foi.

**Abus d'identité :** l'attaquant vole de vrais identifiants d'opérateur. Ses commandes passent toutes les vérifications classiques.

**Attaque combinée :** les deux simultanément.

`[PAUSE]`

Pourquoi les méthodes existantes ne suffisent-elles pas ? `[article §II]`

Les **boucliers formels** ne donnent que deux réponses — autoriser ou bloquer — sans nuance.
Les **détecteurs d'anomalies** signalent des entrées suspectes, mais avec trop de faux positifs, sans mécanisme d'application.
Les **systèmes d'IA sécurisée** ne tiennent pas compte de l'identité de qui envoie la commande.

`[PAUSE]`

**Aucun système existant ne combine** : représentation graphique du réseau, vérification d'identité, décisions graduées formellement vérifiées, et estimation de l'incertitude. `[article §II, tableau comparatif]`

---

## DIAPOSITIVE 5 — Travaux connexes
**~130 mots — ⏱ 1 min 05 sec**
*Source : [article §II, slides]*

`[GESTE : pointer le tableau]`

Ce tableau résume cinq familles de méthodes existantes.

Les **GNN de routage** modélisent très bien la topologie, mais supposent que tout le monde est honnête. Aucune vérification de sécurité.

Les **boucliers formels binaires** garantissent qu'aucune action dangereuse ne s'exécute — mais réponse binaire : tout ou rien.

Les **détecteurs d'anomalies** sont légers, mais trop de fausses alertes et aucun mécanisme d'application.

Les **systèmes agentiques IA / O-RAN** récents sont flexibles — mais sans aucune garantie de sécurité formelle.

`[PAUSE]`

La colonne "Limitation" dit toujours la même chose : chaque méthode résout une partie du problème, jamais l'ensemble. C'est le vide que nous comblons.

---

## DIAPOSITIVE 6 — Formulation du problème
**~160 mots — ⏱ 1 min 20 sec**
*Source : [article §I–III, slides]*

Voici l'observation centrale de notre article : `[article §I fin]`

> « Les méthodes actuelles optimisent la qualité de récupération **avant** de définir une frontière formelle d'admissibilité pour les actions autonomes sous preuves compromises — c'est un **ordre dangereux** en contexte de catastrophe. »

`[PAUSE]`

En clair : tout le monde essaie d'abord de rendre l'IA performante, et sécurise ensuite. Nous proposons l'inverse — définir d'abord ce qu'il est **admissible de faire**, puis optimiser à l'intérieur de cet espace sécurisé.

`[PAUSE]`

Notre bouclier produit **cinq décisions graduées** : `[article §III-A]`

| Décision | Ce qui se passe |
|---|---|
| **Autoriser** | L'action s'exécute normalement |
| **Réduire la portée** | L'action s'exécute sur moins de cellules |
| **Différer** | On attend le cycle suivant |
| **Escalader** | Un opérateur humain est alerté |
| **Bloquer** | L'action est refusée |

`[PAUSE]`

Ce spectre de cinq réponses — au lieu d'un simple oui/non — est ce qui nous permet de ne jamais bloquer une action légitime par erreur tout en restant prudent face aux attaques.

---

## DIAPOSITIVE 7 — Questions de recherche
**~100 mots — ⏱ 50 secondes**
*Source : [article §I, slides]*

Quatre questions de recherche guident notre travail. `[article §I]`

**RQ1 :** Un bouclier zéro-confiance peut-il réduire l'impact des attaques sur la récupération autonome ?

**RQ2 :** Quel est le coût en performance réseau quand on impose ces contraintes de sécurité ?

**RQ3 :** Le système reste-t-il efficace à différentes tailles de réseau et face à différents niveaux d'attaque ?

**RQ4 :** Le système respecte-t-il les contraintes de déploiement réel — notamment la limite des 10 millisecondes ?

`[PAUSE]`

Ces quatre questions structurent toute notre évaluation expérimentale.

---

## DIAPOSITIVE 8 — Objectifs de recherche
**~110 mots — ⏱ 55 secondes**
*Source : [article §I contributions C1–C5, slides]*

À chaque question correspond un objectif concret.

**O1** — Construire le cadre CASTER-ZT avec son bouclier formellement vérifié. `[C1, C2]`

**O2** — Prouver **dix propriétés théoriques** sur le comportement du bouclier. `[C3]`

**O3** — Valider sur une **campagne de 2 420 simulations** : trois tailles de réseau, quatre types d'attaque, quatre méthodes de comparaison, vingt répétitions pour fiabilité statistique. `[C4]`

**O4** — Démontrer que le système respecte les contraintes 6G : moins de 10 ms, moins de 2 mégaoctets de mémoire, fonctionnement autonome sans connexion cloud. `[C4]`

---

## DIAPOSITIVE 9 — Architecture (Vue d'ensemble)
**~210 mots — ⏱ 1 min 45 sec**
*Source : [article §III, slides]*

Voici comment le système fonctionne à chaque cycle de 10 millisecondes.

`[GESTE : pointer le schéma de gauche à droite]`

**Étape 1 — Observer.** Le système reçoit quatre types d'information : l'état de chaque cellule du réseau, les mesures des capteurs, l'action proposée par l'IA, et le jeton d'identité de celui qui propose l'action. `[article §III-A]`

`[PAUSE]`

**Étape 2 — Encoder le réseau.** Un composant appelé **GNN** — réseau de neurones sur graphe — lit l'état du réseau. Pourquoi un graphe ? Parce qu'une cellule ne peut pas être évaluée isolément : la bonne décision pour la cellule A **dépend de l'état de ses voisines** B, C, D. Le GNN capture ces relations de voisinage, qu'une simple liste de valeurs ne pourrait pas représenter. `[article §III-C]`

`[PAUSE]`

**Étape 3 — Proposer une action.** À partir de cette représentation, l'IA choisit la meilleure action parmi six types disponibles — par exemple : redémarrer une cellule (`power-cycle`), réorienter le trafic (`reroute-traffic`), activer une cellule de secours (`activate-backup`). `[article §III-B]`

`[PAUSE]`

**Étape 4 — Évaluer la sécurité.** En parallèle, cinq signaux indépendants sont calculés : la fiabilité de la télémétrie, le risque de l'action, la ressemblance avec un motif d'attaque, l'incertitude de l'IA, et la validité de l'identité. `[article §III-D à III-G]`

`[PAUSE]`

**Étape 5 — Le bouclier décide.** Ces cinq signaux entrent dans le bouclier déterministe, qui produit une des cinq décisions. **L'IA propose. Le bouclier valide.** `[article §III-H]`

---

## DIAPOSITIVE 10 — Architecture (Composants)
**~120 mots — ⏱ 1 min**
*Source : [article §III, Table I, slides]*

Ce tableau liste les cinq composants avec leur taille.

`[GESTE : pointer la colonne Paramètres]`

Le système entier contient environ **20 000 paramètres** et occupe **moins de 2 mégaoctets** en mémoire. `[article §IV-D]`

⚠️ [ANALOGIE] Pour donner une échelle : les grands modèles de langage utilisent des milliards de paramètres. CASTER-ZT est conçu pour tourner sur du matériel embarqué léger, sans connexion cloud.

`[PAUSE]`

Le composant clé à distinguer est la **ligne 5 — le bouclier**, en orange. Il est **déterministe** : ce ne sont pas des poids appris, mais 14 seuils et des règles logiques fixes. `[article §III-H]`

Pourquoi ? Un réseau de neurones peut être attaqué mathématiquement — on peut calculer quelle entrée modifierait sa décision. Un ensemble de règles logiques fixes n'a pas de gradient, donc ce type d'attaque est structurellement impossible. `[article §III-H, discussion]`

---

## DIAPOSITIVE 11 — Méthodologie : L'algorithme du bouclier
**~160 mots — ⏱ 1 min 20 sec**
*Source : [article Algorithm 1, §III-H, slides]*

Regardons les deux colonnes de cette diapositive.

**À gauche : les huit étapes de l'algorithme.** `[article Algorithm 1]`

Les étapes 1 à 7 calculent les cinq signaux de sécurité. L'étape 8 les combine en un **score unique g** — une moyenne pondérée allant de 0 à 1, où 0 signifie "situation très saine" et 1 signifie "situation très suspecte". `[article §III-H équation (5)]`

`[PAUSE]`

**À droite : les règles de décision.** `[article §III-H]`

Ces règles s'appliquent dans l'ordre — la première qui correspond gagne :

- Identité invalide → **bloquer** immédiatement.
- Divergence extrême entre interprétation bénigne et adversariale → **bloquer**.
- Score g faible, confiance suffisante → **autoriser**.
- Score g intermédiaire → **réduire la portée** ou **différer**.
- Score g élevé ou IA très incertaine → **escalader** vers un opérateur humain.
- Sinon → **bloquer**.

`[PAUSE]`

Pour l'entraînement : 2 000 épisodes simulés, soit environ 60 000 décisions annotées. Chaque composant entraîné séparément avec sa propre fonction de coût. `[article §IV-B]`

---

## DIAPOSITIVE 12 — Méthodologie : Les 10 propriétés théoriques
**~150 mots — ⏱ 1 min 15 sec**
*Source : [article §III-I, Propositions 1–10, slides]*

Nous ne nous contentons pas de montrer empiriquement que ça marche. Nous **prouvons mathématiquement** dix propriétés sur le comportement du bouclier. `[article §III-I]`

Je vous en explique les quatre plus importantes en termes simples.

`[PAUSE]`

**P1 — Monotonie :** si la situation devient plus dangereuse, le bouclier ne peut jamais devenir plus permissif. On ne peut pas le tromper en rendant la situation "pire mais acceptable". `[article Prop. 1]`

**P2 — Exclusion des entités non autorisées :** identité invalide = blocage systématique, sans exception. `[article Prop. 2]`

**P6 — Défense en profondeur :** la probabilité qu'une attaque passe les deux portes indépendantes est au plus le **produit** de leurs taux d'erreur. Si chaque porte rate 5 % des attaques, la combinaison n'en rate que 0,25 %. `[article Prop. 6]`

**P9 — Garantie de couverture :** sans aucune hypothèse sur la distribution des données futures, le bouclier bloque les actions dangereuses avec une probabilité garantie — même hors des conditions d'entraînement. `[article Prop. 9]`

`[PAUSE]`

Point clé : le bouclier est **agnostique à la politique**. Si demain vous remplacez notre IA par un autre système, le bouclier fonctionne identiquement. `[article §III-H]`

---

## DIAPOSITIVE 13 — Résultats : RQ1 — Efficacité sécuritaire
**~170 mots — ⏱ 1 min 25 sec**
*Source : [article §IV-C, Table III, slides]*

Voici le tableau de comparaison principal. Cinq méthodes comparées sous une attaque d'identité de haute sévérité, sur 20 répétitions indépendantes. `[article Table III]`

Trois métriques : **RogueDet** = % d'actions malveillantes détectées ; **FalseBlk** = % d'actions légitimes bloquées par erreur ; **ω_rec** = fraction du réseau opérationnel pendant la récupération (1.0 = parfait, 0.0 = catastrophique).

`[GESTE : pointer le tableau ligne par ligne]`

- **CPO-Soft** : zéro détection, ω_rec = 0.201. Sans bouclier, l'attaquant fait des ravages.
- **Agentic-Auto** : 10,5 % détection, 56,8 % de faux blocages. Il bloque plus de légitimes que de malveillants.
- **Shield-Binary** : 88,3 % détection — le meilleur — mais 48,8 % de faux blocages. Presque une action légitime sur deux bloquée par erreur.
- **IF-Trust** : 100 % détection, 0 % faux blocages durs. Semble parfait — j'y reviens dans la prochaine diapositive.
- **CASTER-ZT** : 74,2 % détection, **zéro faux blocage**, ω_rec = 0,733.

`[PAUSE]`

**CASTER-ZT est le seul système à n'avoir jamais bloqué une action légitime par erreur — dans aucune des 20 répétitions, dans aucune condition testée.** `[article Table III, §IV-C]`

---

## DIAPOSITIVE 14 — Résultats : RQ2 — Qualité de récupération et ablation
**~170 mots — ⏱ 1 min 25 sec**
*Source : [article Table IV, Table V ablation, §IV-C–D, slides]*

Pourquoi IF-Trust n'est-il pas la meilleure solution malgré ses 100 % de détection ?

Parce qu'IF-Trust obtient ces résultats en réduisant la portée de **100 % de toutes les actions**, même sans aucune attaque. `[article §IV-C]`

⚠️ [ANALOGIE] C'est comme un gardien qui fouille systématiquement chaque personne — même les employés reconnus — ralentissant tout le monde en permanence.

CASTER-ZT ne contraint que les actions véritablement suspectes.

`[PAUSE]`

Regardons maintenant l'**ablation** — on retire un composant du système et on mesure ce qui se dégrade : `[article Table V]`

- Sans la **vérification de confiance** : détection chute de 74,2 % à 52,4 %, récupération de 0,733 à 0,380. **C'est le composant le plus critique.**
- Sans l'**évaluateur de risque** : détection à 66,5 %, récupération à 0,678.
- Sans la **porte d'autorisation** : la détection monte légèrement. Normal — l'attaquant possède de vraies credentials, cette porte l'aurait laissé passer de toute façon. Ce résultat **confirme que notre modèle de menace est cohérent**. `[article §IV-D]`

---

## DIAPOSITIVE 15 — Résultats : RQ3 — Généralisation
**~140 mots — ⏱ 1 min 10 sec**
*Source : [article Table VI, §IV-E, slides]*

Le système fonctionne-t-il uniquement dans nos conditions initiales ?

Nous avons testé sur **trois tailles de réseau**. `[article Table VI]`

| Taille | Détection | Récupération | Latence |
|---|---|---|---|
| 12 cellules, 2 zones | 74,2 % | 0,733 | 3,07 ms ✅ |
| 36 cellules, 4 zones | 94,9 % | 0,886 | 4,38 ms ✅ |
| 100 cellules, 8 zones | 98,3 % | 0,868 | 10,25 ms ⚠️ |

`[PAUSE]`

**La détection s'améliore avec la taille.** Plus le réseau est grand, plus le GNN a de contexte structurel pour distinguer un comportement normal d'un comportement adversarial. `[article §IV-E]`

**La latence reste dans les limites 6G pour 12 et 36 cellules.** À 100 cellules, on dépasse légèrement avec 10,25 ms — limite honnêtement déclarée. `[article §IV-D]`

**Zéro faux blocage dans toutes les tailles, pour tous les seuils testés.** `[article §IV-E, threshold sensitivity]`

---

## DIAPOSITIVE 16 — Résultats : RQ4 — Conformité déploiement 6G
**~110 mots — ⏱ 55 secondes**
*Source : [article Table VII, §IV-D, slides]*

Voici le profil de déploiement complet. `[article Table VII]`

`[GESTE : pointer la colonne Limite]`

- Latence à 12 cellules : **3,07 ms** — bien en dessous de 10 ms. ✅
- Latence à 36 cellules : **4,38 ms** — conforme. ✅
- Latence à 100 cellules : **10,25 ms** — légèrement au-dessus. ⚠️
- Mémoire : **moins de 2 mégaoctets**. ✅
- Couverture des exigences 6G-AISF : **5 sur 6**. ✅
- Traçabilité et audit : **100 %**. ✅
- Fonctionnement autonome sans cloud : **Oui**. ✅

`[PAUSE]`

Le graphe de convergence à droite montre que chaque composant appris converge proprement — ce qui valide la robustesse du pipeline d'entraînement. `[article Fig. 4]`

---

## DIAPOSITIVE 17 — Progrès et travaux futurs
**~120 mots — ⏱ 1 min**
*Source : [article §V limitations, slides]*

Bilan honnête.

**Accompli :** système complet implémenté, dix preuves théoriques rédigées, 2 420 simulations conduites, article soumis à IEEE TMC. `[slides]`

`[PAUSE]`

**Trois limites principales.** `[article §V]`

**Limite 1 — Attaques sophistiquées.** Un attaquant qui imite parfaitement une télémétrie propre tout en injectant une commande malveillante peut passer inaperçu. Solution future : détecteurs entraînés contre ce type précis d'attaque.

**Limite 2 — Latence à 100 cellules.** Solution identifiée : **quantisation du modèle** — réduire la précision numérique des calculs pour accélérer l'inférence sans changer l'architecture.

**Limite 3 — Politique par imitation.** La prochaine étape est un apprentissage par essai-erreur en ligne, sous contraintes du bouclier.

---

## DIAPOSITIVE 18 — Conclusion
**~120 mots — ⏱ 1 min**
*Source : [article §V, slides]*

Pour conclure.

Nous avons proposé **CASTER-ZT** — le premier système qui combine représentation graphique du réseau, évaluation multi-signaux de la sécurité, et bouclier déterministe avec garanties mathématiques formelles, pour la récupération autonome en contexte de catastrophe. `[article §I contributions]`

`[PAUSE]`

Les résultats clés : `[article §IV]`

- **Zéro faux blocages** — dans aucune des 20 répétitions, dans aucune condition.
- **3,07 ms de latence** — compatible avec les exigences 6G à l'échelle primaire.
- **Moins de 2 mégaoctets** — déployable sur matériel embarqué léger, sans cloud.
- **5 sur 6 exigences 6G-AISF satisfaites.**

`[PAUSE]`

Le message fondamental :

`[PAUSE — EMPHASE]`

> **Sécurité d'abord ne signifie pas utilité en dernier.** `[article §V conclusion]`

Il est possible d'imposer des frontières de sécurité formelles à une IA autonome tout en maintenant une récupération réseau significative.

Je vous remercie.

---

## DIAPOSITIVE 19 — Références
**Aucune narration. Diapositive pour le jury uniquement.**

---

## TABLEAU DE TIMING STRICT

| Diapo | Contenu | Mots | Durée |
|---|---|---|---|
| 1 | Titre | 60 | 30 sec |
| 2 | Plan | 55 | 30 sec |
| 3 | Contexte — récupération | 170 | 1 min 25 |
| 4 | Contexte — sécurité | 150 | 1 min 15 |
| 5 | Travaux connexes | 130 | 1 min 05 |
| 6 | Formulation | 160 | 1 min 20 |
| 7 | Questions de recherche | 100 | 50 sec |
| 8 | Objectifs | 110 | 55 sec |
| 9 | Architecture — vue | 210 | 1 min 45 |
| 10 | Architecture — composants | 120 | 1 min |
| 11 | Méthodologie — bouclier | 160 | 1 min 20 |
| 12 | Méthodologie — propriétés | 150 | 1 min 15 |
| 13 | Résultats RQ1 | 170 | 1 min 25 |
| 14 | Résultats RQ2 | 170 | 1 min 25 |
| 15 | Résultats RQ3 | 140 | 1 min 10 |
| 16 | Résultats RQ4 | 110 | 55 sec |
| 17 | Limites & futur | 120 | 1 min |
| 18 | Conclusion | 120 | 1 min |
| **TOTAL** | | **~2 305** | **~19 min 40 sec** |

> ✅ Marge de sécurité de 20 secondes intégrée pour les transitions.

---

## CINQ CORRECTIONS APPLIQUÉES (RÉSUMÉ)

| Problème (v1) | Correction (v2) |
|---|---|
| Script ~28 min | Chaque diapositive recadrée au compte de mots exact. Total : 19 min 40 sec. |
| Noms d'actions incorrects (POWER_BOOST, CELL_DEACTIVATION) | Remplacés par noms de l'article : `power-cycle`, `reroute-traffic`, `cell-reconfig`, `activate-backup`. `[article §III-B]` |
| Affirmations non sourcées ("photo de téléphone", "clignement d'œil", "10% scope-reduction clean") | Supprimées ou marquées `⚠️ [ANALOGIE]`. Toutes les données chiffrées renvoient à `[article §X]`. |
| "Ablation" non défini | Défini : "on retire un composant et on mesure ce qui se dégrade". |
| Propriétés P7–P10 en jargon | Seules P1, P2, P6, P9 présentées, en langage clair, avec numérotation de l'article. |
| "Quantisation du modèle" non expliqué | Défini : "réduire la précision numérique des calculs pour accélérer l'inférence". |

---

## AIDE-MÉMOIRE : 5 QUESTIONS PROBABLES ET RÉPONSES COURTES

**Q : Pourquoi 74,2 % de détection seulement ?**
> C'est le point d'opération choisi pour équilibrer détection et impact opérationnel. `[article §IV-E threshold sensitivity]` À 100 cellules : 98,3 %. Et c'est le seul système avec zéro faux blocage. Shield-Binary fait 88,3 % mais bloque 48,8 % d'actions légitimes.

**Q : Pourquoi le bouclier n'est-il pas lui-même un réseau de neurones ?**
> Un réseau de neurones peut être attaqué par gradient — on calcule quelle entrée ferait changer sa décision. Un ensemble de règles logiques fixes n'a pas de gradient, ce type d'attaque est structurellement impossible. `[article §III-H]`

**Q : Comment les dix preuves ont-elles été vérifiées ?**
> Chaque preuve suit une structure mathématique standard et figure dans le document de preuves supplémentaires soumis avec l'article. P6 utilise l'indépendance conditionnelle, P7 le théorème de Hoeffding, P9 la théorie conforme. `[article Supplemental Proofs]`

**Q : Qu'est-ce qui distingue ceci d'un IDS classique ?**
> Un IDS détecte et alerte. CASTER-ZT détecte, décide, exécute une réponse graduée parmi cinq, consigne une trace immutable, et prouve formellement des garanties sur son comportement. `[article §III]`

**Q : Le système fonctionne-t-il sans aucune attaque ?**
> Oui — contrainte de conception explicite. `[article §IV-C clean condition]` Sous conditions normales, le bouclier n'impose aucun blocage dur. L'opération est quasi-transparente.


# Soutenance de thèse — Notes de présentation
**Georges Parfait Djimefo Kapen — Polytechnique Montréal — Juillet 2026**
**Durée totale : 30 minutes | ~25 diapositives | ~1 min/diapo en moyenne**

---

## GUIDE DE RYTHME

| Section | Diapositives | Durée |
|---------|--------------|-------|
| Titre + Plan | 2 | 1 min |
| Contexte et motivation | 2 | 3 min |
| Problème et objectifs | 2 | 3 min |
| Méthodologie | 2 | 2 min |
| Article 1 — GAPF | 3 | 5 min |
| Article 2 — CALASH | 3 | 5 min |
| Article 3 — CASTER-ZT | 2 | 4 min |
| Discussion et synthèse | 3 | 4 min |
| Contributions et impact | 2 | 2 min |
| Limites et perspectives | 2 | 1 min |
| Conclusion | 1 | 1 min |
| Remerciements | — | 30 sec |

---

## DIAPO 1 — Titre

> *Restez immobile trois secondes. Regardez le jury avant de parler. Puis, pendant l'intro, tournez-vous aussi vers la salle — famille, amis, invités. C'est leur moment aussi.*

« Bonjour à toutes et à tous. Je m'appelle Georges Parfait Djimefo Kapen. Je soutiens aujourd'hui ma thèse de doctorat intitulée : *Routage intelligent piloté par l'IA et récupération autonome sécurisée dans les réseaux de capteurs sans fil intégrés à la 6G pour la surveillance de catastrophes.*

Ce travail a été réalisé sous la direction du Professeur Ranwa Al Mallah et du co-directeur Professeur Samuel Pierre, au laboratoire LARIM de Polytechnique Montréal.

Au cours des 30 prochaines minutes, je vais vous expliquer pourquoi les réseaux de capteurs qui surveillent les catastrophes naturelles doivent être plus efficaces, plus écologiques et plus sûrs — et comment j'ai construit une solution complète pour y parvenir. »

---

## DIAPO 2 — Plan

> *Rapide. Il s'agit simplement d'orienter l'auditoire.*

« Voici le plan de ma présentation. Je commencerai par le contexte — pourquoi cette recherche est importante. Je vous présenterai ensuite trois articles, chacun résolvant un défi majeur. Je terminerai par une discussion des résultats, des limites et des perspectives. »

---

## DIAPO 3 — Contexte : catastrophes naturelles et surveillance

> *Cette diapositive parle à tout le monde, technique ou non. Prenez le temps.*

« Commençons par un chiffre qui devrait nous préoccuper tous. Entre 2000 et 2019, on a recensé plus de 7 000 grandes catastrophes naturelles dans le monde — séismes, inondations, ouragans. Cela représente 4,2 milliards de personnes touchées, 1,2 million de morts et près de 3 000 milliards de dollars de pertes économiques.

En 2023 seulement : 398 catastrophes, 95 000 décès. Et le changement climatique aggrave la situation — les scientifiques prévoient une augmentation de 30 % de la fréquence des événements météorologiques extrêmes dans les prochaines décennies.

Le Cadre de Sendai, adopté par 187 pays en 2015, fixe un objectif clair : renforcer les systèmes d'alerte précoce pour que les populations puissent évacuer avant que la catastrophe ne frappe.

La question est donc : *comment surveiller une zone sinistrée en temps réel ?* La réponse : grâce aux réseaux de capteurs sans fil — de petits appareils autonomes et peu coûteux, disséminés sur une zone, qui transmettent en continu des données. C'est précisément l'objet de cette thèse. »

---

## DIAPO 4 — Les réseaux de capteurs : potentiel et contraintes

> *Court. Poser la tension d'ingénierie.*

« Les réseaux de capteurs sont puissants : ils peuvent couvrir de grandes zones de manière autonome, ils sont peu coûteux, et ils fonctionnent même après une catastrophe. Mais ils ont des contraintes sévères.

Imaginez un capteur comme un appareil alimenté par une petite pile de montre : environ 0,5 joule d'énergie au total. Pas de recharge possible. Mémoire très limitée. Et il est physiquement exposé à la catastrophe même qu'il surveille.

Par ailleurs, nous entrons maintenant dans l'ère de la 6G — la prochaine génération de communications mobiles, avec des fréquences térahertz, des surfaces réfléchissantes intelligentes et une latence ultra-faible. Cela ouvre de nouvelles possibilités pour les réseaux de capteurs, mais aussi de nouvelles complexités à gérer.

Nous avons donc un environnement exigeant. Voyons maintenant ce qu'il faut précisément résoudre. »

---

## DIAPO 5 — Trois défis fondamentaux

> *Trois problèmes, trois articles. Annoncer la structure clairement.*

« Cette thèse identifie trois défis fondamentaux qu'aucune approche existante n'a résolus simultanément.

**Défi 1 — L'énergie.** Le routage — la manière dont chaque capteur transmet ses données — est le premier facteur déterminant la durée de vie d'un réseau de capteurs. Les méthodes existantes basées sur l'IA nécessitent des dizaines de milliers de paramètres par agent. Elles sont tout simplement trop lourdes pour des appareils embarqués, et aucune ne combine intelligemment plusieurs stratégies selon la topologie du réseau.

**Défi 2 — Le carbone.** La plupart des gens pensent à la consommation énergétique. Mais en réalité, le plus grand impact carbone d'un capteur provient de sa *fabrication* — le silicium, la batterie, le boîtier — et non de son fonctionnement. Le carbone incorporé lors de la production est un million de fois supérieur à celui consommé par paquet transmis. Aucun protocole de routage existant ne tient compte de ce cycle de vie complet.

**Défi 3 — La sécurité.** Lorsque l'on intègre l'IA dans la boucle de contrôle, on crée une nouvelle surface d'attaque. Un nœud capteur peut être compromis. La politique de l'IA peut être manipulée. Les défenses existantes sont binaires : autoriser ou bloquer. Mais dans une zone sinistrée, tout bloquer paralyse le réseau. Il faut de la nuance.

Ces trois défis — efficacité, durabilité, sécurité — sont ce que cette thèse résout. »

---

## DIAPO 6 — Questions et objectifs de recherche

> *Lire la question principale lentement et clairement. C'est l'ancre de la thèse.*

« La question de recherche principale qui guide cette thèse est la suivante :

*"Comment concevoir une pile de protocoles de routage intelligents — efficace en énergie, durable en carbone, et sécurisée — pour des réseaux de capteurs natifs IA intégrés à la 6G ?"*

J'ai traduit cette question en trois questions spécifiques et trois objectifs précis — un par article. Je ne les lirai pas tous maintenant, mais je veux que vous remarquiez que chaque objectif dispose d'une cible mesurable : taux de livraison de paquets supérieur à 98 %, réduction carbone de 33 %, zéro faux positif en sécurité, le tout dans le budget de latence de 10 millisecondes imposé par la norme 6G. »

---

## DIAPO 7 — Approche méthodologique

> *Adressez-vous à toute la salle, pas seulement au jury. La famille ne connaît pas la DSR.*

« Sur le plan méthodologique, cette thèse suit une approche appelée Recherche en Science du Design. Concrètement, cela signifie que l'objectif n'est pas seulement de comprendre un phénomène, mais de *construire quelque chose* — et de prouver que ça fonctionne. Comme un architecte qui ne se contente pas d'étudier les bâtiments, mais qui en conçoit un, le construit, et mesure s'il tient debout. Ici, j'ai construit trois outils logiciels, et je les ai testés rigoureusement.

Ces trois outils suivent une progression délibérée : le premier résout l'efficacité énergétique, le deuxième étend le travail à l'impact carbone, le troisième ajoute la sécurité. Et — c'est important — ils se protègent mutuellement. Ce n'est pas trois projets séparés mis bout à bout. C'est une seule pile intégrée. »

---

## DIAPO 8 — Protocole expérimental commun

> *Établir la crédibilité rapidement.*

« Les trois articles partagent une philosophie d'évaluation commune : des simulations ancrées dans des données réelles. Nous avons utilisé de vraies traces de capteurs du laboratoire Intel Berkeley, de vraies données d'intensité carbone de l'API du réseau électrique britannique, et de vrais modèles sismiques calibrés sur le séisme Turquie-Syrie 2023 — magnitude 7,8.

Au total, sur les trois articles, nous avons effectué plus de 23 800 simulations. Tous les résultats reportent des intervalles de confiance à 95 %. Ce n'est pas une étude à petite échelle. »

---

## DIAPO 9 — GAPF : Architecture

> *Premier article. Prendre le temps sur le schéma — c'est l'idée centrale.*

« Permettez-moi de vous présenter le premier article : GAPF — Graph-Attentive Policy Fusion, ou Fusion de Politiques par Attention sur Graphe.

L'idée centrale est simple mais puissante. Au lieu d'entraîner un grand réseau de neurones pour contrôler le routage — ce qui serait trop lourd pour les capteurs —, j'ai pris deux agents IA déjà entraînés, QMIX et QTRAN, bloqué leurs poids, et construit un méta-contrôleur léger par-dessus.

Ce méta-contrôleur fait deux choses. Le GCN, ou Réseau de Convolution sur Graphe, lit la topologie du réseau de capteurs et produit un résumé compact de l'état courant. Ensuite, le CAS — le Sélecteur Contextuel d'Algorithme — utilise ce résumé pour décider quel expert écouter dans la situation présente.

Imaginez un entraîneur qui observe deux spécialistes. L'un est excellent pour coordonner des équipes très regroupées. L'autre est meilleur pour des formations plus dispersées. L'entraîneur regarde le terrain et décide qui écouter. C'est GAPF.

L'ensemble du méta-contrôleur n'a que 1 473 paramètres entraînables. À titre de comparaison, un seul agent MARL traditionnel en compte 39 000. Nous sommes 26 fois plus légers. »

---

## DIAPO 10 — GAPF : Pourquoi la fusion fonctionne

> *Commencez par l'analogie. Ne dites le nom technique qu'après.*

« Pourquoi la fusion fonctionne-t-elle ? Parce que les deux algorithmes que j'ai combinés sont bons dans des situations différentes — et mauvais dans des situations différentes. QMIX excelle quand les capteurs sont proches et doivent se coordonner serré. QTRAN est meilleur quand les interactions sont plus complexes. En laissant un méta-contrôleur choisir lequel écouter selon la situation, on ne garde que le meilleur de chacun.

Pensez à deux médecins spécialistes : l'un est cardiologue, l'autre pneumologue. Un généraliste intelligent ne choisit pas l'un pour toujours — il écoute le cardiologue quand il s'agit du cœur, et le pneumologue quand il s'agit des poumons. C'est exactement ce que fait GAPF.

Nous avons aussi résolu un problème classique de décision multi-critères : comment comparer énergie, fiabilité et rapidité sur une seule échelle ? Nous avons introduit un mécanisme mathématique qui garantit formellement que si une solution est meilleure sur tous les critères à la fois, elle sera toujours classée au-dessus. Cette garantie n'existe dans aucune méthode existante. »

---

## DIAPO 11 — GAPF : Résultats clés

> *Les chiffres — les énoncer clairement et avec assurance.*

« Les résultats parlent d'eux-mêmes. Par rapport à la meilleure méthode existante, QMIX :

- Le taux de livraison de paquets est passé de 46 à 67 % jusqu'à 98 % et plus — une amélioration de 43 à 111 %.
- La consommation énergétique a chuté à moins de la moitié — 2 à 3,5 fois plus faible.
- Le modèle tient dans 5,8 kilo-octets — déployable directement sur un microcontrôleur ARM à 10 dollars, sans compression.
- La mémoire d'entraînement est passée de 14 gigaoctets à moins d'un gigaoctet.

Ceci a été validé sur 21 000 épisodes de simulation couvrant 7 scénarios réseau différents, de 20 à 100 capteurs. »

---

## DIAPO 12 — CALASH : Architecture

> *Deuxième article. Expliquer l'intuition sur le cycle de vie — c'est contre-intuitif.*

« Le deuxième article est CALASH — Carbon-Aware Lifecycle Autonomous Self-Healing, soit Récupération Autonome Consciente du Carbone sur Cycle de Vie.

Avant d'expliquer l'architecture, permettez-moi de partager l'intuition centrale qui le motive. Quand vous pensez à l'empreinte carbone d'un capteur, vous pensez probablement à l'électricité qu'il consomme. Mais la fabrication du capteur — le silicium, la batterie, le boîtier — coûte un million de fois plus de carbone par paquet que l'électricité consommée pendant le fonctionnement. La seule façon d'amortir ce carbone incorporé est de maximiser le nombre de paquets utiles livrés par le capteur au cours de sa vie.

C'est le principe fondamental : la stratégie de routage la plus écologique est celle qui fait vivre le réseau plus longtemps et livre plus de données efficacement.

CALASH met en oeuvre cela à travers quatre piliers, chacun gérant une partie du cycle de vie :

- Le premier pilier, CADR, adapte la compression des données selon la propreté du réseau électrique à l'instant T. Quand l'électricité vient principalement du charbon, on compresse davantage pour transmettre moins. Quand elle vient du solaire ou de l'hydraulique, on envoie plus de données.
- Le deuxième pilier, CARE, prend les décisions de routage avec un mécanisme mathématique — inspiré des travaux du mathématicien Lyapunov sur la stabilité des systèmes — qui garantit qu'on maximise les livraisons de données TOUT EN respectant un budget carbone à long terme. Imaginez un comptable qui gère un budget mensuel : il peut dépenser plus un jour, mais il sait qu'il devra compenser les jours suivants. C'est exactement ce que fait ce mécanisme, appliqué au carbone.
- Le troisième pilier, SHDR, est le composant d'auto-réparation : après une catastrophe, des capteurs meurent. Ce pilier surveille en permanence l'état du réseau et reconstruit automatiquement les chemins de communication — comme un GPS qui recalcule l'itinéraire quand une route est coupée.
- Le quatrième pilier, LSE, est la couche de comptabilité carbone : il calcule, pour chaque paquet livré, le coût carbone total depuis la fabrication du capteur jusqu'à sa fin de vie, selon la norme internationale ISO 14040.

Tout cela fonctionne au-dessus d'une couche physique 6G double bande — utilisant à la fois le sub-térahertz pour le haut débit et le sub-6 GHz classique pour la couverture, avec des surfaces réfléchissantes intelligentes. »

---

## DIAPO 13 — CALASH : Les quatre piliers

> *Cette diapo est un résumé visuel. Parlez lentement, montrez chaque pilier du doigt.*

« Pour résumer les quatre piliers en une phrase chacun : CADR compresse les données quand l'électricité est sale. CARE route les paquets en respectant un budget carbone avec garantie mathématique. SHDR répare automatiquement le réseau après une catastrophe. Et LSE mesure le coût carbone total, de la fabrication à la mise au rebut.

Ce qui est remarquable, c'est que ces quatre piliers fonctionnent ensemble en temps réel, sur un microcontrôleur qui coûte quelques euros. »

---

## DIAPO 14 — CALASH : Résultats clés

> *À nouveau, les chiffres avec assurance.*

« Résultats de CALASH, comparés à LEACH — la référence standard :

- Durée de vie du réseau : de 931 à 1 486 rounds — 60 % plus long.
- Taux de livraison de paquets : 82,9 % — élevé même dans des conditions de catastrophe difficiles.
- Empreinte carbone par paquet : de 13,42 à 8,99 grammes de CO2 équivalent — une réduction de 33 %.

Ceci a été validé sur 390 simulations avec 30 graines Monte Carlo indépendantes, en utilisant des données réelles d'intensité carbone de quatre réseaux électriques nationaux — France, Allemagne, Pologne, Norvège — montrant que les gains sont robustes quel que soit le mix énergétique. »

---

## DIAPO 15 — CASTER-ZT : Architecture

> *Troisième article. Commencer par la menace, puis la solution.*

« Le troisième article est CASTER-ZT — et il aborde un problème rarement discuté dans la recherche sur les réseaux de capteurs : que se passe-t-il quand l'IA elle-même est compromise ?

Lorsque vous intégrez l'IA dans la boucle de contrôle d'un réseau de surveillance de catastrophes, vous faites confiance à cette IA pour prendre les bonnes décisions de routage. Mais que se passe-t-il si un noeud a été piraté et diffuse de fausses informations ? Si la politique de l'IA — entraînée à récupérer après des pannes — a été manipulée pour envoyer les paquets dans le vide ?

Les solutions existantes sont binaires : autoriser ou bloquer. Mais dans une mission critique, bloquer toute décision suspecte paralyse le réseau. Il faut des réponses graduées.

CASTER-ZT introduit un bouclier de décision à confiance zéro — un concept de cybersécurité qui signifie : *ne faire confiance à personne par défaut, vérifier systématiquement tout le monde*. C'est le même principe que les aéroports : même si vous avez votre carte d'embarquement, vous passez quand même le contrôle de sécurité.

Concrètement : chaque décision proposée par l'IA passe par un pipeline de vérification en quatre questions. La source est-elle fiable ? L'action est-elle anormalement risquée ? Le comportement dévie-t-il de la normale ? L'agent est-il autorisé à prendre ce type de décision ?

Selon les réponses, le bouclier prend l'une des cinq décisions visibles en bas de la diapositive — Autoriser, Réduire la portée, Différer, Escalader, ou Bloquer. Ce n'est pas binaire. C'est gradué, comme un agent de sécurité qui peut soit laisser passer, soit demander une fouille, soit appeler son supérieur, soit bloquer.

Fait crucial : le bouclier lui-même ne fait pas d'apprentissage automatique — il ne peut donc pas être trompé par des données fabriquées pour le manipuler. Il applique des règles logiques déterministes. C'est ce qui le rend certifiable pour des systèmes critiques. »

---

## DIAPO 16 — CASTER-ZT : Résultats

> *Zéro faux positif est le titre — l'insister.*

« Résultats de CASTER-ZT :

- Détection de politique malveillante : 74 à 98 % selon le type d'attaque.
- Faux positifs : zéro pour cent — le bouclier ne bloque jamais incorrectement une action légitime. Jamais. C'est une garantie formelle, pas simplement un résultat empirique.
- Score de récupération : 0,733 — 3,7 à 5,2 fois supérieur aux méthodes existantes.
- Latence de décision : 3,07 millisecondes — largement dans le budget temps de 10 ms imposé par la norme O-RAN pour les boucles de contrôle 6G.

Cela a été validé sur 2 420 simulations, testées contre quatre scénarios d'attaque incluant des politiques malveillantes coordonnées et des hallucinations hors distribution. »

---

## DIAPO 17 — Synergies de la pile de protocoles

> *C'est l'apport clé de la thèse au-delà des trois contributions individuelles.*

« Permettez-moi maintenant de prendre du recul pour expliquer pourquoi ces trois frameworks forment une pile plutôt que trois articles séparés.

Les synergies sont réelles et directionnelles :

- GAPF livre les données efficacement — ce qui réduit directement le carbone opérationnel. Un routage plus efficace signifie moins d'énergie par paquet, donc moins de CO2.
- CALASH réduit le volume de données par compression — ce qui réduit le nombre de transmissions — ce qui réduit la surface d'attaque que CASTER-ZT doit surveiller.
- CASTER-ZT protège l'ensemble de la pile — sans lui, un seul noeud compromis pourrait invalider tous les gains d'efficacité et de durabilité de GAPF et CALASH.

La pile complète coûte environ 27 000 paramètres entraînables — comparable à un seul agent MARL traditionnel. Nous atteignons efficacité, durabilité ET sécurité pour le coût d'un seul algorithme de référence. »

---

## DIAPO 18 — Synthèse quantitative globale

> *Le jury regardera ce tableau attentivement. Parcourez-le ligne par ligne.*

« Laissez-moi vous donner le tableau complet. Ce tableau résume tous les gains sur les trois articles par rapport aux meilleures références existantes :

- Livraison de paquets : de 46 à 67 % jusqu'à 98 %. Amélioration de 43 à 111 %.
- Énergie : 2 à 3,5 fois moins par paquet.
- Paramètres : 26 fois moins — 1 473 contre 39 000.
- Durée de vie du réseau : 60 % plus longue.
- Empreinte carbone : 33 % réduite.
- Sécurité : 74 à 98 % de détection avec zéro faux positif — la meilleure méthode précédente avait 48,8 % de faux positifs.
- Latence de décision : 3,3 fois plus rapide que le budget O-RAN.
- Couverture des 12 critères de lacune identifiés dans la revue de littérature : 12 sur 12.

Aucune approche existante ne couvre plus d'un de ces 12 critères. Nous couvrons les 12. »

---

## DIAPO 19 — Déployabilité TinyML

> *Cette diapositive parle à tout le monde. Regardez la salle entière.*

« L'un des résultats pratiques les plus importants de cette thèse est la taille du système. La pile complète — les trois frameworks combinés — tient dans 103 kilo-octets. Pour vous donner une idée : c'est moins qu'un emoji animé sur WhatsApp.

Cela signifie que l'intelligence artificielle complète — celle qui gère l'énergie, le carbone, ET la sécurité — peut tourner sur une puce qui coûte 5 dollars et se tient dans votre ongle. Pas besoin d'un serveur. Pas besoin d'une connexion cloud permanente.

Pourquoi est-ce si important ? Parce que 95 % des décès causés par les catastrophes naturelles surviennent dans des pays à revenus faibles ou moyens. Si notre système avait besoin de matériel à 500 dollars par capteur, il ne serait jamais déployé là où il est le plus nécessaire. En tenant dans 5 dollars de silicium, il peut aller partout. »

---

## DIAPO 20 — Six contributions scientifiques originales

> *Lire chaque contribution avec une phrase de contexte.*

« Cette thèse compte six contributions originales reconnues par la communauté scientifique. Permettez-moi de les présenter en langage clair.

Premièrement : j'ai créé la première méthode qui combine intelligemment plusieurs algorithmes d'IA pour le routage de capteurs, en choisissant le meilleur selon le contexte. Cela n'existait pas.

Deuxièmement : j'ai introduit un mécanisme mathématique qui garantit que quand on compare plusieurs critères à la fois — énergie, fiabilité, rapidité — le classement final est toujours cohérent et ne peut pas favoriser une solution inférieure. Une garantie formelle qui manquait dans tous les travaux précédents.

Troisièmement : j'ai créé la première métrique qui mesure l'empreinte carbone complète d'un réseau de capteurs — de la fabrication à la mise au rebut — en grammes de CO₂ par paquet livré. Un outil de mesure standardisé qui n'existait nulle part.

Quatrièmement : j'ai construit le premier protocole de routage qui tient simultanément deux promesses mathématiquement prouvées : livrer un maximum de données ET rester dans un budget carbone.

Cinquièmement : j'ai conçu le premier bouclier de sécurité pour réseaux IA qui répond de façon graduée — cinq niveaux de décision — avec des garanties formelles écrites noir sur blanc sous forme de propositions mathématiques.

Sixièmement, et peut-être le plus important : j'ai démontré que l'efficacité, la durabilité et la sécurité ne sont pas trois objectifs contradictoires. Ils se renforcent. C'est un résultat de fond qui change la façon dont on doit concevoir ces systèmes. »

---

## DIAPO 21 — Impact et alignement avec les ODD

> *Court — connecter aux parties prenantes réelles.*

« Ces contributions ont des implications concrètes pour trois groupes de parties prenantes.

Pour l'industrie : le modèle GAPF de 5,8 ko élimine le besoin de passerelles périphériques coûteuses. L'amélioration de 60 % de la durée de vie réduit les coûts de maintenance. La métrique LCI fournit un outil standardisé pour les rapports de durabilité dans le cadre de la réglementation CSRD. Le bouclier auditable simplifie la certification IEC 62443.

Pour les gouvernements : la LCI offre un indicateur IoT standardisé que les régulateurs peuvent imposer. GAPF et CALASH contribuent directement à deux indicateurs du Cadre de Sendai — C-2 et C-6 — qui mesurent la couverture des systèmes d'alerte précoce. Tous les algorithmes sont en accès libre, sans dépendance à un fournisseur.

Pour la société et les Objectifs de Développement Durable des Nations Unies : nous contribuons à l'ODD 9 (infrastructures résilientes), l'ODD 11 (réduire les décès dus aux catastrophes), l'ODD 12 (production durable), l'ODD 13 (action climatique), et l'ODD 16 (institutions transparentes). »

---

## DIAPO 22 — Limites reconnues

> *Soyez direct et confiant. Connaître ses limites démontre la maturité scientifique.*

« Je souhaite être transparent sur les limites de ce travail.

Sur le plan méthodologique : tous les résultats sont basés sur des simulations. Nous avons utilisé des données réelles pour la calibration, mais nous n'avons pas encore validé sur du matériel physique. Le modèle de catastrophe utilise une distribution spatiale gaussienne — adéquate pour les séismes, mais pas pour les inondations à évolution lente ou les feux de forêt. La couche physique 6G utilise des modèles analytiques, pas de tracé de rayons 3D complet.

Sur le plan technique : les trois frameworks n'ont pas été intégrés et testés en tant que système unifié. Leurs performances au-delà de 200 noeuds ne sont pas caractérisées. Le modèle de sécurité suppose des adversaires statiques — des attaquants adaptatifs qui apprennent à contourner le bouclier ne sont pas couverts. Et nous n'avons pas conduit d'études utilisateurs avec des intervenants d'urgence.

Ce sont des limites honnêtes. Elles définissent précisément ce que la prochaine phase de cette recherche doit aborder. »

---

## DIAPO 23 — Perspectives de recherche

> *Tournée vers l'avenir et énergique. C'est une ouverture, pas une clôture.*

« La feuille de route à venir est claire.

À court terme — un à deux ans — la priorité est l'intégration : combiner les trois couches en un seul système et tester sur du vrai matériel comme le Zolertia RE-Mote ou le NVIDIA Jetson. Nous avons aussi besoin de modèles de catastrophe plus réalistes.

À moyen terme — deux à quatre ans — l'apprentissage fédéré permet l'entraînement sans centraliser les données sensibles. Les jumeaux numériques fournissent un environnement de simulation continu pour les mises à jour de politiques avant déploiement. La vérification formelle par des prouveurs de théorèmes comme Coq permettrait la certification du bouclier pour des systèmes critiques pour la sécurité.

À long terme — plus de quatre ans — nous regardons les réseaux non-terrestres : satellites LEO, plateformes haute altitude, drones comme stations de base mobiles après une catastrophe. Nous regardons aussi la standardisation — soumettre la métrique LCI et le framework à confiance zéro à l'ISO, l'ETSI et le 3GPP.

Et au-delà de la surveillance des catastrophes — les mêmes principes s'appliquent à l'agriculture de précision, aux villes intelligentes, à la santé connectée et aux essaims de drones. »

---

## DIAPO 24 — Conclusion

> *C'est le moment. Calme, clair, confiant.*

« Pour conclure.

Cette thèse a proposé une pile de protocoles complète pour le routage intelligent dans des réseaux de capteurs intégrés à la 6G pour la surveillance de catastrophes, construite autour de trois frameworks complémentaires.

GAPF résout le problème énergétique : 1 473 paramètres, taux de livraison supérieur à 98 %, consommation énergétique réduite de 2 à 3,5 fois.

CALASH résout le problème du carbone : quatre piliers, garanties de Lyapunov, réduction carbone de 33 %, durée de vie du réseau 60 % plus longue.

CASTER-ZT résout le problème de sécurité : cinq décisions graduées, zéro faux positif, 10 propositions formelles, 3,07 millisecondes par décision.

Le message central de cette thèse est le suivant : l'IA, conçue avec parcimonie, conscience environnementale, et vérification systématique, est un outil fiable pour les environnements critiques.

Nous n'avons pas besoin de modèles plus grands. Nous avons besoin de modèles plus intelligents. »

---

## DIAPO 25 — Merci / Questions

> *Arrêtez-vous. Respirez. Souriez. Laissez le silence faire son effet.*

« Je vous remercie de votre attention.

Je suis maintenant disponible pour répondre à vos questions. »

---

## DIAPOSITIVES DE SECOURS — Aide-mémoire rapide

### Secours 1 — Garanties de convergence et fondements théoriques
- **GAPF** : QMIX converge dans les fonctions monotones (contrainte IGM). QTRAN couvre un espace plus large via la factorisation affine. Le CAS agit comme un réducteur de variance (analogue au stacking de Wolpert).
- **CALASH** : Dérive de Lyapunov plus pénalité. Converge à O(1/V) de l'optimum. V=100 donne -33 % de LCI avec une latence acceptable. La borne CDL prouve la convergence simultanée sur le taux de livraison et le budget carbone.
- **CASTER-ZT** : 10 propositions prouvées par construction logique. Conservatisme monotone, exclusion d'actuation non autorisée, couverture de calibration conforme, prix de sécurité borné.

### Secours 2 — Analyse des lacunes (12 critères)
Aucune approche existante ne couvrait plus d'1 critère sur 12 identifiés. Notre pile couvre les 12. Les critères comprennent : routage écoénergétique, conscience de la topologie, fusion MARL, scalarisation de Pareto, métrique carbone du cycle de vie, compression consciente du carbone, garanties de budget carbone, auto-réparation, PHY 6G, détection de politique malveillante, décisions graduées, preuves formelles de sécurité.

### Secours 3 — Complexité Dec-POMDP
Le Dec-POMDP optimal est NEXP-complet. Le CTDE (QMIX, QTRAN) est une approximation structurée qui réduit l'espace d'actions jointes de |A|^n à somme de |A_i|. GAPF ajoute un niveau méta de sélection d'experts. Le résultat de 98 % de taux de livraison n'est pas une preuve d'optimalité globale — c'est une approximation de haute qualité validée empiriquement sur 21 000 épisodes.

---

## QUESTIONS FRÉQUEMMENT ATTENDUES DU JURY

**Q : Pourquoi ne pas entraîner une seule politique de bout en bout plutôt que de fusionner QMIX et QTRAN ?**
> « Entraîner une politique monolithique unique nécessite que l'infrastructure d'entraînement s'adapte à n agents — 39 000 paramètres chacun. GAPF exploite la complémentarité de deux spécialistes déjà éprouvés et n'ajoute que 1 473 paramètres par-dessus. Le paradigme de portefeuille est bien établi en optimisation combinatoire. La réduction des paramètres par 26 et la garantie formelle de monotonicité de Pareto sont des arguments en faveur de cette approche par rapport à une approche monolithique. »

**Q : La simulation utilise un modèle gaussien de catastrophe — est-ce réaliste ?**
> « Le modèle gaussien capture la décroissance spatiale de l'impact à partir d'un épicentre sismique. Il a été calibré sur les données réelles de ShakeMap du séisme Turquie-Syrie 2023. Pour les catastrophes à évolution lente comme les inondations ou les feux de forêt, un modèle différent serait nécessaire — c'est explicitement reconnu comme une limite et motive le travail sur des modèles de catastrophe étendus prévu en année 1 de l'agenda de recherche future. »

**Q : Comment justifiez-vous l'hypothèse 6G pour les réseaux de capteurs ?**
> « L'intégration 6G se fait via l'architecture O-RAN — les capteurs eux-mêmes ne fonctionnent pas en 6G. Les têtes de cluster communiquent avec la station de base via un lien double bande 6G. C'est réaliste étant donné l'horizon de déploiement 6G en 2030, qui correspond au moment où les systèmes de surveillance de catastrophes construits aujourd'hui seront en opération. »

**Q : CASTER-ZT annonce zéro faux positif — est-ce une garantie ou un résultat empirique ?**
> « Les deux. Le taux de zéro faux positif est une conséquence formelle de la propriété de correction du bouclier (Proposition 1) : le bouclier ne bloque que lorsque le score composite de conservatisme dépasse un seuil calibré. Une action légitime, par définition, a un risque faible et une confiance élevée — elle ne franchira jamais ce seuil. Le 0 % est ensuite confirmé empiriquement sur 2 420 simulations. »

**Q : Comment la métrique LCI se compare-t-elle aux métriques environnementales existantes dans l'IoT ?**
> « Les métriques existantes mesurent l'énergie par paquet (Joules/paquet) ou la durée de vie opérationnelle. Elles ignorent le carbone incorporé — le carbone émis lors de la fabrication. La métrique LCI que nous définissons intègre le carbone de fabrication, opérationnel et de fin de vie en une seule valeur en gCO2eq par paquet utile, selon la norme ISO 14040. C'est la première métrique de ce type pour les protocoles de routage dans les réseaux de capteurs. Son adoption comme référence standard est une recommandation clé à la communauté de recherche. »

**Q : Pourquoi n'y a-t-il pas eu de déploiement sur matériel réel ?**
> « Le déploiement sur matériel est l'étape suivante — c'est le premier point de l'agenda de recherche à court terme. La décision de compléter d'abord l'évaluation par simulation était délibérée : nous devions valider les algorithmes sur un grand espace de paramètres (21 000 épisodes, 7 scénarios) qui serait infaisable sur du matériel physique. L'analyse de faisabilité (Annexe E) montre la compatibilité théorique avec le Cortex-M4 pour une latence d'inférence inférieure à 1 ms — faisant de l'étape matérielle une validation, non une exploration. »

---

*Bonne chance. Vous avez fait le travail. Faites-lui confiance.*

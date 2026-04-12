#!/usr/bin/env python3
"""
Generate a tailored Word (.docx) CV in FRENCH for AI Developer.
Run:  python3 generate_cv_deloitte_fr.py
Output: CV_Deloitte_AI_Developer_FR.docx
"""

from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import os

# ── Colours ─────────────────────────────────────────────────────────────────
BLUE = RGBColor(0x1F, 0x4E, 0x79)
BLACK = RGBColor(0x00, 0x00, 0x00)
GREY = RGBColor(0x4D, 0x4D, 0x4D)

doc = Document()

# ── Page margins ────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(10)
style.font.color.rgb = BLACK
style.paragraph_format.space_before = Pt(0)
style.paragraph_format.space_after = Pt(0)

# ── Helpers ─────────────────────────────────────────────────────────────────
def heading(text):
    p = doc.add_paragraph()
    p.space_before = Pt(8)
    p.space_after = Pt(3)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = BLUE
    run.font.name = "Calibri"
    pPr = p._p.get_or_add_pPr()
    pPr.append(parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="1" w:color="1F4E79"/>'
        f'</w:pBdr>'
    ))


def body(text, space_after=2):
    p = doc.add_paragraph()
    p.space_after = Pt(space_after)
    r = p.add_run(text)
    r.font.size = Pt(9.5)
    r.font.name = "Calibri"
    return p


def bullet(text, bold_start=""):
    p = doc.add_paragraph(style="List Bullet")
    p.space_before = Pt(0)
    p.space_after = Pt(1)
    p.paragraph_format.left_indent = Inches(0.3)
    if bold_start:
        rb = p.add_run(bold_start)
        rb.bold = True
        rb.font.size = Pt(9.5)
        rb.font.name = "Calibri"
    r = p.add_run(text)
    r.font.size = Pt(9.5)
    r.font.name = "Calibri"
    return p


def italic_bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.space_before = Pt(0)
    p.space_after = Pt(1)
    p.paragraph_format.left_indent = Inches(0.3)
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9.5)
    r.font.name = "Calibri"
    return p


def exp_header(title, org, dates):
    p = doc.add_paragraph()
    p.space_before = Pt(3)
    p.space_after = Pt(1)
    p.paragraph_format.tab_stops.add_tab_stop(
        Cm(17.4), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES
    )
    r1 = p.add_run(title)
    r1.bold = True
    r1.font.size = Pt(10)
    r1.font.name = "Calibri"
    r2 = p.add_run(f"  |  {org}")
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = GREY
    r2.font.name = "Calibri"
    r3 = p.add_run(f"\t{dates}")
    r3.font.size = Pt(9.5)
    r3.font.color.rgb = GREY
    r3.font.name = "Calibri"
    r3.italic = True


def pub_entry(num, title, authors, status, bullets_list):
    p = doc.add_paragraph()
    p.space_before = Pt(3)
    p.space_after = Pt(0)
    r1 = p.add_run(f"[{num}] ")
    r1.bold = True
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = BLUE
    r1.font.name = "Calibri"
    r2 = p.add_run(title)
    r2.italic = True
    r2.font.size = Pt(9.5)
    r2.font.name = "Calibri"
    pa = doc.add_paragraph()
    pa.space_after = Pt(1)
    ra = pa.add_run(authors)
    ra.italic = True
    ra.font.size = Pt(9)
    ra.font.color.rgb = GREY
    ra.font.name = "Calibri"
    rs = pa.add_run(f"  ({status})")
    rs.italic = True
    rs.font.size = Pt(9)
    rs.font.color.rgb = GREY
    rs.font.name = "Calibri"
    for b in bullets_list:
        bullet(b)


def conf_entry(header_text, detail_text):
    p = doc.add_paragraph()
    p.space_before = Pt(2)
    p.space_after = Pt(0)
    r = p.add_run(header_text)
    r.bold = True
    r.font.size = Pt(9.5)
    r.font.name = "Calibri"
    p2 = doc.add_paragraph()
    p2.space_after = Pt(1)
    p2.paragraph_format.left_indent = Inches(0.2)
    r2 = p2.add_run(detail_text)
    r2.italic = True
    r2.font.size = Pt(9)
    r2.font.name = "Calibri"


# ============================================================================
#  EN-TÊTE
# ============================================================================
tp = doc.add_paragraph()
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
tp.space_after = Pt(0)
nr = tp.add_run("GEORGES PARFAIT DJIMEFO KAPEN")
nr.bold = True
nr.font.size = Pt(16)
nr.font.color.rgb = BLUE
nr.font.name = "Calibri"

sp = doc.add_paragraph()
sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
sp.space_after = Pt(1)
sr = sp.add_run("Développeur IA | IA Agentique & Systèmes Infonuagiques")
sr.font.size = Pt(10)
sr.font.color.rgb = GREY
sr.font.name = "Calibri"

cp = doc.add_paragraph()
cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
cp.space_after = Pt(2)
cr = cp.add_run(
    "Montréal, Québec, Canada  ·  +1 514-245-3182  ·  gpdk2025@gmail.com"
)
cr.font.size = Pt(9.5)
cr.font.color.rgb = GREY
cr.font.name = "Calibri"

# ============================================================================
#  PROFIL
# ============================================================================
heading("Profil")
body(
    "Développeur IA avec expérience pratique en conception et déploiement de "
    "systèmes d'IA agentiques en production, flux de travail multi-agents "
    "basés sur des LLM et agents conversationnels RAG à l'échelle de "
    "l'entreprise sur AWS. Solide expertise en évaluation et analyse "
    "comparative de modèles d'IA, architecture infonuagique native "
    "(sans serveur, conteneurs), automatisation CI/CD et pipelines de "
    "données ETL/ELT. Doctorat prévu été 2026 avec recherche en IA, "
    "réseaux de neurones sur graphes, apprentissage par renforcement "
    "multi-agents et cybersécurité. Aptitude démontrée à communiquer "
    "les compromis techniques aux cadres dirigeants et aux parties "
    "prenantes non techniques. Innovation, travail d'équipe, leadership "
    "et orientation vers les résultats.",
    space_after=3,
)

# ============================================================================
#  COMPÉTENCES TECHNIQUES
# ============================================================================
heading("Compétences techniques")
skills = [
    ("LLM / Agents",
     "LangChain, LangGraph, LangSmith, MCP, RAG (FAISS), CRAG, RAGAS, "
     "Claude (Haiku, Opus), Kiro"),
    ("IA / ML",
     "PyTorch, TensorFlow, Scikit-Learn, MARL (QMIX, QTRAN), GNN, DQN, "
     "NLP, Vision par ordinateur, LLM"),
    ("Infonuagique",
     "AWS (SageMaker, Bedrock, EKS, Lambda, CloudWatch, S3, ECR, "
     "CloudFormation), OpenStack, Kubernetes, Docker"),
    ("DevOps / IaC",
     "CI/CD (GitHub Actions, CodeBuild, OIDC), Git, Jenkins, GitLab, "
     "Terraform, Infrastructure en tant que code"),
    ("Données",
     "PySpark, Databricks, Snowflake, Delta Lake, SQL, Bases de données "
     "relationnelles, ETL/ELT"),
    ("Langages", "Python, Java, C++, PHP, SQL, R, JavaScript, TypeScript"),
    ("Web / API",
     "REST APIs, FastAPI, Streamlit, React, Angular, Node.js, D3.js, "
     "Plotly, Dash, Power BI, Tableau"),
    ("Méthodes",
     "Agile/Scrum, TDD, Patrons de conception, Modélisation statistique, "
     "MLOps, Gouvernance IA"),
]
for cat, items in skills:
    p = doc.add_paragraph()
    p.space_after = Pt(1)
    r1 = p.add_run(f"{cat} : ")
    r1.bold = True
    r1.font.size = Pt(9.5)
    r1.font.name = "Calibri"
    r2 = p.add_run(items)
    r2.font.size = Pt(9.5)
    r2.font.name = "Calibri"

# ============================================================================
#  EXPÉRIENCE PERTINENTE
# ============================================================================
heading("Expérience pertinente")

exp_header("Stagiaire ML — IA Agentique & Systèmes Infonuagiques",
           "Ericsson, Montréal", "2026")
bullet("Conçu et déployé un système autonome d'IA agentique RAG en production "
       "qui automatise la détection d'anomalies dans les journaux d'unités "
       "radio en télécommunications, remplaçant la revue manuelle pour les "
       "clients entreprise.")
bullet("Construit un flux de travail multi-agents LLM : agent ReAct à "
       "6 outils orchestré par Claude Haiku 4.5 sur Bedrock (notation "
       "SageMaker, RAG FAISS, modèle physique RF, classification de "
       "motifs, surveillance CloudWatch), reproduisant le raisonnement "
       "d'un analyste.")
bullet("Évalué et comparé les modèles fondamentaux avec le score de "
       "fidélité/pertinence RAGAS et une notation de confiance méta-cognitive "
       "fondée sur des preuves (ÉLEVÉ/MOYEN/FAIBLE) pour optimiser les "
       "compromis performance-coût.")
bullet("Entraîné un SLM à double attention personnalisé atteignant un "
       "F1 de 90,6 %, une précision de 99,97 % et une latence d'inférence "
       "de 1 ms/journal sur AWS SageMaker.")
bullet("Conçu un pipeline map-reduce à l'échelle de la production : "
       "triage → regroupement par signature de panne → investigation "
       "parallèle par agents → synthèse adaptative inter-grappes. "
       "Traite 120+ anomalies en ~12 min.")
bullet("Construit un tableau de bord Streamlit pour les dirigeants "
       "exposant les métriques de précision, d'utilisation, de latence et "
       "de coût par requête pour les décisions de la direction.")
bullet("Déployé en tant que pod K8s sur EKS via tunnel Cloudflare ; "
       "construit un pipeline événementiel (S3 → Lambda → SQS → "
       "worker K8s → S3 → alertes SNS) pour la haute disponibilité.")
bullet("Conçu une boucle de réentraînement entièrement autonome : "
       "déclenchée par la dérive + hebdomadaire via EventBridge, avec "
       "promotion automatique uniquement lorsque le F1 du nouveau modèle "
       "dépasse la référence en production (gouvernance et surveillance IA).")
bullet("Mis en œuvre un pipeline CI/CD en 7 étapes (GitHub Actions + "
       "CodeBuild avec OIDC) : test → analyse de sécurité OWASP → "
       "infra CloudFormation → validation pré-prod → déploiement → "
       "test de fumée → retour arrière automatique. Zéro clé IAM statique.")
bullet("Rédigé 131 tests automatisés avec un gardien de tests adaptatif "
       "basé sur l'AST assurant une couverture de 100 % des fonctions "
       "en production.")
italic_bullet("Pile technologique : Python, AWS (SageMaker, Bedrock, EKS, "
              "Lambda, SQS, SNS, S3, ECR, CloudFormation, CloudWatch), "
              "LangChain, LangGraph, LangSmith, FAISS, MCP, Claude, Kiro, "
              "Docker, Kubernetes, CI/CD, Terraform.")

exp_header("Développeur IA I — Systèmes de données d'entreprise",
           "Intact Corporation financière, Montréal", "2022–2024")
bullet("Ingérer et traiter des données à grande échelle.")
bullet("Travailler dans un environnement d'assurance.")
bullet("Surveiller les pipelines et développer des solutions de tests "
       "automatisés assurant la qualité des données et la fiabilité "
       "des systèmes.")
italic_bullet("Pile technologique : PySpark, SQL, Databricks, Snowflake, "
              "AWS, Shell, Git.")

# ============================================================================
#  EXPÉRIENCE ADDITIONNELLE
# ============================================================================
heading("Expérience additionnelle")

additional = [
    ("Chargé de cours", "Polytechnique Montréal, Montréal", "2025–2026",
     ["Enseigner le cours de programmation procédurale Python ; communiquer "
      "des concepts techniques complexes à des auditoires non techniques."]),
    ("Chargé de cours", "Polytechnique Montréal, Montréal", "2022–2023",
     ["Enseigner le cours de programmation procédurale Python."]),
    ("Auxiliaire scientifique — MOOC IA",
     "Université de Montréal, Montréal", "2021–2022",
     ["Concevoir des cours et travaux pratiques en apprentissage supervisé "
      "(Python)."]),
    ("Ingénieur statisticien économiste contractuel",
     "Ministère du Tourisme et des Loisirs, Cameroun", "2012–2014",
     ["Analyser des données."]),
    ("Professeur associé de statistique et probabilité",
     "Université Protestante d'Afrique Centrale, Cameroun", "2010–2012",
     ["Enseigner les cours de statistique et de probabilité."]),
    ("Chargé de cours en analyse de données",
     "ISSEA (Institut Sous-régional de Statistique et d'Économie "
     "Appliquée), Cameroun", "2009–2010",
     ["Enseigner le cours d'analyse de données (R)."]),
]
for title, org, dates, bullets_list in additional:
    exp_header(title, org, dates)
    for b in bullets_list:
        bullet(b)

# ============================================================================
#  PUBLICATIONS
# ============================================================================
heading("Publications")

pub_entry(
    1,
    "Energy-Efficient and Near Real-Time Routing Algorithm for Disaster "
    "Monitoring in Wireless Sensor Networks",
    "G. P. Djimefo Kapen, R. Al Mallah, S. Pierre — Polytechnique Montréal",
    "Soumis",
    ["Conçu GAPF, un cadre novateur de méta-apprentissage fusionnant des "
     "politiques MARL via un encodeur GCN avec seulement 1 473 paramètres.",
     "Atteint ≥98 % de livraison de paquets, 2–3,5× moins d'énergie, "
     "13× moins de mémoire que les référentiels."],
)

pub_entry(
    2,
    "Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for "
    "6G-Integrated Disaster Sensor Networks",
    "G. P. Djimefo Kapen, R. Al Mallah, S. Pierre — Polytechnique Montréal",
    "Soumis",
    ["Proposé CALASH, le premier protocole optimisant conjointement "
     "l'intensité carbone du cycle de vie via un moteur hybride "
     "Lyapunov–DQN.",
     "Atteint 60 % de durée de vie réseau plus longue et 33 % de LCI "
     "inférieure aux référentiels."],
)

pub_entry(
    3,
    "Zero-Trust Shielded Graph-Structured Decision Control for Secure "
    "Autonomous Recovery in AI-Native 6G Networks",
    "G. P. Djimefo Kapen, R. Al Mallah, S. Pierre — Polytechnique Montréal",
    "Soumis",
    ["Conçu CASTER-ZT, combinant la prise de décision basée sur les GNN "
     "avec un bouclier d'admissibilité zéro confiance formellement borné ; "
     "sécurité et conformité d'entreprise par conception.",
     "Atteint 74–98 % de détection de nœuds malveillants avec zéro "
     "faux positif, latence de 3 ms dans le budget O-RAN de 10 ms."],
)

# ============================================================================
#  PROJETS SÉLECTIONNÉS
# ============================================================================
heading("Projets sélectionnés")

projects = [
    ("Stagiaire en ingénierie des données",
     "Intact Corporation financière, Montréal", "2022",
     ["Manipuler des données (PySpark, SQL, Databricks, Snowflake, AWS)."]),
    ("Projet intégrateur — IATA",
     "Polytechnique Montréal, Montréal", "2021",
     ["« Flight Data eXchange — Développer un outil initial et contextuel "
      "d'évaluation des données de vol. » (Dash, Python, React, Electron, "
      "Axios)."]),
    ("Stagiaire en initiation à la recherche",
     "Polytechnique Montréal, Montréal", "2020–2021",
     ["Modélisation de reconnaissance vocale pour paiements bancaires "
      "sécurisés ; apprentissage profond (Python) déployé sur Android "
      "(Java)."]),
    ("Projet de TAL",
     "Polytechnique Montréal, Montréal", "2021",
     ["Extraction de mots-clés à partir de textes ainsi que leur type "
      "(Python)."]),
    ("Projet de visualisation de données — Chaire de recherche en fiscalité",
     "Polytechnique Montréal, Montréal", "2021",
     ["Application web pour comparer les taxes et taux par année "
      "(Plotly.js, D3)."]),
    ("Entrepreneur / Stagiaire en initiation à la recherche",
     "Polytechnique Montréal, Montréal", "2020",
     ["Modélisation de reconnaissance faciale intégrant les biais raciaux "
      "et de genre ; apprentissage profond (Python)."]),
    ("Stagiaire en programmation",
     "FLEX GROUP, Laval", "2019–2020",
     ["Modélisation de reconnaissance optique de caractères automatique "
      "(Python, PHP)."]),
    ("Stagiaire pour maîtrise en statistique appliquée",
     "Banque Internationale du Cameroun pour l'Épargne et le Crédit, "
     "Cameroun", "2006",
     ["Modèles mathématiques de prévision des recettes et dépenses "
      "d'une banque (R)."]),
]
for title, org, dates, bullets_list in projects:
    exp_header(title, org, dates)
    for b in bullets_list:
        bullet(b)

# ============================================================================
#  FORMATION
# ============================================================================
heading("Formation")

education = [
    ("Doctorat en génie informatique (Été 2026)",
     "Polytechnique Montréal, Montréal, Canada",
     ["Routage piloté par l'IA, réseautique écoresponsable et sécurité "
      "zéro confiance pour les réseaux de capteurs 6G."]),
    ("Diplôme d'ingénieur en génie logiciel",
     "Polytechnique Montréal, Montréal, Canada",
     ["Concentration : Intelligence artificielle — Science des données."]),
    ("Maîtrise en statistique appliquée",
     "École Nationale Supérieure Polytechnique de Yaoundé (ENSPY), "
     "Yaoundé, Cameroun",
     ["Équivalence : Maîtrise en probabilités — statistiques."]),
    ("Maîtrise en mathématiques",
     "Université de Yaoundé I, Yaoundé, Cameroun",
     ["Équivalence : Diplôme d'études supérieures spécialisées (DESS) "
      "en mathématiques."]),
]
for degree, school, details in education:
    p = doc.add_paragraph()
    p.space_before = Pt(2)
    p.space_after = Pt(0)
    r = p.add_run(degree)
    r.bold = True
    r.font.size = Pt(9.5)
    r.font.name = "Calibri"
    p2 = doc.add_paragraph()
    p2.space_after = Pt(0)
    r2 = p2.add_run(school)
    r2.italic = True
    r2.font.size = Pt(9)
    r2.font.color.rgb = GREY
    r2.font.name = "Calibri"
    for d in details:
        bullet(d)

# ============================================================================
#  CERTIFICATIONS
# ============================================================================
heading("Licences et certifications")

certs = [
    ("AWS Certified Cloud Practitioner (CLF-C01)",
     "Parcours de préparation à la certification (Pluralsight), Montréal"),
    ("AWS Certified Developer — Associate (DVA-C02)",
     "Parcours de préparation à la certification (Pluralsight), Montréal"),
]
for cert_name, prep in certs:
    p = doc.add_paragraph(style="List Bullet")
    p.space_before = Pt(1)
    p.space_after = Pt(1)
    p.paragraph_format.left_indent = Inches(0.3)
    r1 = p.add_run(cert_name)
    r1.font.size = Pt(9.5)
    r1.font.name = "Calibri"
    r2 = p.add_run(f"\n{prep}")
    r2.italic = True
    r2.font.size = Pt(9)
    r2.font.color.rgb = GREY
    r2.font.name = "Calibri"

# ============================================================================
#  CONFÉRENCES
# ============================================================================
heading("Conférences et séminaires")

conf_entry(
    "Présentation orale — PolyCongrès 2026, Polytechnique Montréal, "
    "Montréal (Mars–Avr. 2026)",
    "« Energy-Efficient and Near Real-Time Routing for Disaster Monitoring "
    "in Wireless Sensor Networks — Graph-Attentive Policy Fusion (GAPF). »",
)
conf_entry(
    "Présentation orale — 20e Conf. de l'Association africaine des "
    "scientifiques de l'insecte, Yaoundé, Cameroun (Oct. 2013)",
    "Djimefo P., Tchuente M. & Le Gall P. — « Biogéographie des "
    "communautés d'insectes à l'aide de méthodes de regroupement. »",
)
conf_entry(
    "Affiche — 29e Conf. annuelle de la Société internationale de "
    "biostatistique clinique, Copenhague, Danemark (Août 2008)",
    "« Estimation de l'incidence du VIH à partir d'enquêtes transversales "
    "répétées. »",
)
conf_entry(
    "Présentation orale — ANMSA (Réseau Africain de Statistique "
    "Mathématique et ses Applications), Franceville, Gabon (Jan. 2008)",
    "« Épidémiologie du VIH au Cameroun : estimation de l'incidence à "
    "partir des données de prévalence. »",
)

# ============================================================================
#  BÉNÉVOLAT
# ============================================================================
heading("Bénévolat")
bullet("Bénévole à la branche IEEE de Polytechnique Montréal, "
       "Montréal, 2018.")
bullet("Bénévole à la conférence ConFoo, Montréal, 2018.")

# ============================================================================
#  SAUVEGARDE
# ============================================================================
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "CV_Deloitte_AI_Developer_FR.docx")
doc.save(out_path)
print(f"✅  CV Word (FR) sauvegardé : {out_path}")

#!/usr/bin/env python3
"""
Generate a tailored Word (.docx) CV for Deloitte – AI Developer (Edmonton).
Run:  python3 generate_cv_deloitte.py
Output: CV_Deloitte_AI_Developer.docx
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
#  HEADER
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
sr = sp.add_run("AI Developer | Agentic AI & Cloud Systems")
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
#  PROFILE
# ============================================================================
heading("Profile")
body(
    "AI developer with hands-on experience designing and deploying "
    "production-grade agentic AI systems, multi-agent LLM workflows, "
    "and enterprise-scale RAG chatbots on AWS. Strong background in "
    "AI evaluation & benchmarking, cloud-native architecture (serverless, "
    "containers), CI/CD automation, and ETL/ELT data pipelines. "
    "PhD expected Summer 2026 with research in AI, graph neural networks, "
    "multi-agent reinforcement learning, and cybersecurity. Proven ability "
    "to communicate technical trade-offs to executives and non-technical "
    "stakeholders. Innovation, teamwork, leadership, and results-oriented.",
    space_after=3,
)

# ============================================================================
#  TECHNICAL SKILLS
# ============================================================================
heading("Technical Skills")
skills = [
    ("LLM / Agents",
     "LangChain, LangGraph, LangSmith, MCP, RAG (FAISS), CRAG, RAGAS, "
     "Claude (Haiku, Opus), Kiro"),
    ("AI / ML",
     "PyTorch, TensorFlow, Scikit-Learn, MARL (QMIX, QTRAN), GNN, DQN, "
     "NLP, Computer Vision, LLMs"),
    ("Cloud",
     "AWS (SageMaker, Bedrock, EKS, Lambda, CloudWatch, S3, ECR, "
     "CloudFormation), OpenStack, Kubernetes, Docker"),
    ("DevOps / IaC",
     "CI/CD (GitHub Actions, CodeBuild, OIDC), Git, Jenkins, GitLab, "
     "Terraform, Infrastructure as Code"),
    ("Data",
     "PySpark, Databricks, Snowflake, Delta Lake, SQL, Relational "
     "Databases, ETL/ELT"),
    ("Languages", "Python, Java, C++, PHP, SQL, R, JavaScript, TypeScript"),
    ("Web / APIs",
     "REST APIs, FastAPI, Streamlit, React, Angular, Node.js, D3.js, "
     "Plotly, Dash, Power BI, Tableau"),
    ("Methods",
     "Agile/Scrum, TDD, Design Patterns, Statistical Modeling, MLOps, "
     "AI Governance"),
]
for cat, items in skills:
    p = doc.add_paragraph()
    p.space_after = Pt(1)
    r1 = p.add_run(f"{cat}: ")
    r1.bold = True
    r1.font.size = Pt(9.5)
    r1.font.name = "Calibri"
    r2 = p.add_run(items)
    r2.font.size = Pt(9.5)
    r2.font.name = "Calibri"

# ============================================================================
#  RELEVANT EXPERIENCE
# ============================================================================
heading("Relevant Experience")

exp_header("ML Intern — Agentic AI & Cloud Systems",
           "Ericsson, Montréal", "2026")
bullet("Designed and deployed a production RAG Autonomous Agentic AI system "
       "that automates telecom radio unit log anomaly detection, replacing "
       "manual review for enterprise clients.")
bullet("Built a multi-agent LLM workflow: 6-tool ReAct agent orchestrated "
       "by Claude Haiku 4.5 on Bedrock (SageMaker scoring, FAISS RAG, "
       "RF physics world model, pattern classification, CloudWatch health "
       "monitoring), replicating analyst reasoning.")
bullet("Evaluated and benchmarked foundation models with RAGAS "
       "faithfulness/relevancy scoring and evidence-based meta-cognition "
       "confidence grading (HIGH/MEDIUM/LOW) to optimize performance-cost "
       "trade-offs.")
bullet("Trained a custom Dual-Attention SLM achieving F1 90.6%, 99.97% "
       "accuracy, and 1 ms/log inference latency on AWS SageMaker.")
bullet("Engineered a production-scale map-reduce pipeline: triage → cluster "
       "by failure signature → parallel agent investigation → adaptive "
       "cross-cluster synthesis. Handles 120+ anomalies in ~12 min.")
bullet("Built an executive-facing Streamlit dashboard exposing accuracy, "
       "usage, latency, and cost-per-query metrics for leadership decisions.")
bullet("Deployed as a K8s pod on EKS via Cloudflare tunnel; built an "
       "event-driven pipeline (S3 → Lambda → SQS → K8s worker → S3 → "
       "SNS alerts) for high availability.")
bullet("Designed a fully autonomous retraining loop: drift-triggered + "
       "weekly via EventBridge, with auto-promotion only when new model F1 "
       "exceeds production baseline (AI governance & monitoring).")
bullet("Implemented a 7-stage CI/CD pipeline (GitHub Actions + CodeBuild "
       "with OIDC): test → OWASP security scan → CloudFormation infra → "
       "staging gate → deploy → smoke test → auto-rollback. Zero static "
       "IAM keys.")
bullet("Authored 131 automated tests with an AST-based adaptive test "
       "guardian ensuring 100% production function coverage.")
italic_bullet("Stack: Python, AWS (SageMaker, Bedrock, EKS, Lambda, SQS, "
              "SNS, S3, ECR, CloudFormation, CloudWatch), LangChain, "
              "LangGraph, LangSmith, FAISS, MCP, Claude, Kiro, Docker, "
              "Kubernetes, CI/CD, Terraform.")

exp_header("AI Developer I — Enterprise Data Systems",
           "Intact Financial Corporation, Montréal", "2022–2024")
bullet("Ingest and process large-scale data.")
bullet("Work in an insurance environment.")
bullet("Monitor pipelines and develop automated testing solutions ensuring "
       "data quality and system reliability.")
italic_bullet("Stack: PySpark, SQL, Databricks, Snowflake, AWS, Shell, Git.")

# ============================================================================
#  ADDITIONAL EXPERIENCE
# ============================================================================
heading("Additional Experience")

additional = [
    ("Lecturer", "Polytechnique Montréal, Montréal", "2025–2026",
     ["Teach the Python procedural programming course; communicate complex "
      "technical concepts to non-technical audiences."]),
    ("Lecturer", "Polytechnique Montréal, Montréal", "2022–2023",
     ["Teach the Python procedural programming course."]),
    ("Scientific Assistant — MOOC AI",
     "Université de Montréal, Montréal", "2021–2022",
     ["Design courses and practical work in supervised learning (Python)."]),
    ("Contractual Statistical Economist Engineer",
     "Ministry of Tourism and Recreation, Cameroon", "2012–2014",
     ["Analyze data."]),
    ("Associate Professor of Statistics & Probability",
     "Protestant University of Central Africa, Cameroon", "2010–2012",
     ["Teach statistics and probability courses."]),
    ("Part-time Lecturer in Data Analysis",
     "ISSEA (Sub-regional Institute of Statistics and Applied Economics), Cameroon",
     "2009–2010",
     ["Teach the Data Analysis course (R)."]),
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
    "Submitted",
    ["Designed GAPF, a novel meta-learning framework fusing MARL policies "
     "via a GCN encoder with only 1,473 parameters.",
     "Achieved ≥98% packet delivery, 2–3.5× less energy, "
     "13× less memory than baselines."],
)

pub_entry(
    2,
    "Carbon-Aware Autonomous Data Reduction and Self-Healing Routing for "
    "6G-Integrated Disaster Sensor Networks",
    "G. P. Djimefo Kapen, R. Al Mallah, S. Pierre — Polytechnique Montréal",
    "Submitted",
    ["Proposed CALASH, the first protocol jointly optimizing Lifecycle "
     "Carbon Intensity via a hybrid Lyapunov–DQN engine.",
     "Achieved 60% longer network lifetime and 33% lower LCI "
     "than baselines."],
)

pub_entry(
    3,
    "Zero-Trust Shielded Graph-Structured Decision Control for Secure "
    "Autonomous Recovery in AI-Native 6G Networks",
    "G. P. Djimefo Kapen, R. Al Mallah, S. Pierre — Polytechnique Montréal",
    "Submitted",
    ["Designed CASTER-ZT, combining GNN-based decision making with a "
     "formally bounded zero-trust admissibility shield; enterprise security "
     "and compliance by design.",
     "Achieved 74–98% rogue detection with zero false positives, "
     "3 ms latency within O-RAN 10 ms budget."],
)

# ============================================================================
#  SELECTED PROJECTS
# ============================================================================
heading("Selected Projects")

projects = [
    ("Data Engineering Intern",
     "Intact Financial Corporation, Montréal", "2022",
     ["Manipulate data (PySpark, SQL, Databricks, Snowflake, AWS)."]),
    ("Integrator Project — IATA",
     "Polytechnique Montréal, Montréal", "2021",
     ['"Flight Data eXchange — Develop an initial and contextual flight '
      'data assessment tool." (Dash, Python, React, Electron, Axios).']),
    ("Undergraduate Research Initiation Intern",
     "Polytechnique Montréal, Montréal", "2020–2021",
     ["Voice Recognition modeling for secure bank payments; "
      "Deep Learning (Python) deployed on Android (Java)."]),
    ("NLP Project",
     "Polytechnique Montréal, Montréal", "2021",
     ["Extraction of keywords from texts as well as their type (Python)."]),
    ("Data Visualization Project — Chaire de recherche en fiscalité",
     "Polytechnique Montréal, Montréal", "2021",
     ["Web application to compare taxes and rates by year (Plotly.js, D3)."]),
    ("Entrepreneur / Research Initiation Intern",
     "Polytechnique Montréal, Montréal", "2020",
     ["Face Recognition modeling integrating racial and gender bias; "
      "Deep Learning (Python)."]),
    ("Programming Intern",
     "FLEX GROUP, Laval", "2019–2020",
     ["Modeling of Automatic Optical Character Recognition (Python, PHP)."]),
    ("Intern for Master's in Applied Statistics",
     "International Bank of Cameroon for Savings and Credit, Cameroon",
     "2006",
     ["Mathematical models for forecasting a bank's income and "
      "expenses (R)."]),
]
for title, org, dates, bullets_list in projects:
    exp_header(title, org, dates)
    for b in bullets_list:
        bullet(b)

# ============================================================================
#  EDUCATION
# ============================================================================
heading("Education")

education = [
    ("PhD in Computer Engineering (Summer 2026)",
     "Polytechnique Montréal, Montréal, Canada",
     ["AI-driven routing, carbon-aware networking, and zero-trust security "
      "for 6G sensor networks."]),
    ("Engineering Diploma in Software Engineering",
     "Polytechnique Montréal, Montréal, Canada",
     ["Concentration: Artificial Intelligence — Data Sciences."]),
    ("Master's Degree in Applied Statistics",
     "Advanced National School of Engineering (ENSPY), Yaoundé, Cameroon",
     ["Equivalency: Master's in Probability — Statistics."]),
    ("Master's Degree in Mathematics",
     "University of Yaoundé I, Yaoundé, Cameroon",
     ["Equivalency: Specialized Higher Studies Diploma (DESS) in "
      "Mathematics."]),
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
heading("Licenses & Certifications")

certs = [
    ("AWS Certified Cloud Practitioner (CLF-C01)",
     "Certification Prep Path (Pluralsight), Montréal"),
    ("AWS Certified Developer — Associate (DVA-C02)",
     "Certification Prep Path (Pluralsight), Montréal"),
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
#  CONFERENCES
# ============================================================================
heading("Conferences & Seminars")

conf_entry(
    "Oral Presentation — PolyCongrès 2026, Polytechnique Montréal, "
    "Montréal (Mar–Apr 2026)",
    '"Energy-Efficient and Near Real-Time Routing for Disaster Monitoring '
    'in Wireless Sensor Networks — Graph-Attentive Policy Fusion (GAPF)."',
)
conf_entry(
    "Oral Presentation — 20th Conf. African Assoc. of Insect Scientists, "
    "Yaoundé, Cameroon (Oct 2013)",
    'Djimefo P., Tchuente M. & Le Gall P. — "Biogeography of communities '
    'of insects using clustering methods."',
)
conf_entry(
    "Poster — 29th Annual Conf. Int. Society for Clinical Biostatistics, "
    "Copenhagen, Denmark (Aug 2008)",
    '"HIV incidence estimation from repeated cross-sectional surveys."',
)
conf_entry(
    "Oral Presentation — ANMSA (African Network of Mathematical "
    "Statistics and its Applications), Franceville, Gabon (Jan 2008)",
    '"HIV epidemiology in Cameroon: Estimating incidence from '
    'prevalence data."',
)

# ============================================================================
#  VOLUNTEERING
# ============================================================================
heading("Volunteering")
bullet("Volunteer at the IEEE branch of Polytechnique Montréal, "
       "Montréal, 2018.")
bullet("Volunteer at the ConFoo conference, Montréal, 2018.")

# ============================================================================
#  SAVE
# ============================================================================
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "CV_Deloitte_AI_Developer.docx")
doc.save(out_path)
print(f"✅  Word CV saved to: {out_path}")

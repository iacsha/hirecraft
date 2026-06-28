r"""
resume_builder_ats.py — ATS-safe single-column resume PDF.

Why this exists:
  The main resume_builder.py uses a TWO-COLUMN table layout with a colored
  sidebar. That looks great to humans but many ATS parsers (Workday/Greenhouse/
  Taleo) read columns out of order. Use THIS builder for ATS portals; use
  resume_builder.py for LinkedIn / recruiter-forwarded / human-reviewed channels.

ATS-safe design:
  - Single column, NO tables, NO text boxes, NO images, NO skill bars
  - Standard section headings (SUMMARY, CORE SKILLS, KEY PROJECT, EXPERIENCE,
    CERTIFICATIONS), black text on white
  - Skills are plain text keywords (no proficiency levels)
  - Strongest proof (KEY PROJECT) surfaced right after skills, near the top
  - Selectable text via Edge headless print-to-PDF

SETUP
-----
Copy config.example.json to config.json and fill in your details.
You can also add a "skills" object to resume_content.json to override
DEFAULT_SKILLS on a per-role basis.

Usage:
    python resume_builder_ats.py <path_to_resume_content.json>

Output:
    <jobhunt_root>/<company>/<name_slug>-Resume.pdf
"""

import html
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parent
CONFIG_PATH = REPO_ROOT / "config.json"

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else REPO_ROOT / "config.example.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_cfg     = load_config()
NAME_SLUG = _cfg.get("name_slug", "Your-Name")
JOBHUNT  = Path(_cfg.get("jobhunt_root", str(REPO_ROOT.parent)))
HTMLOUT  = str(REPO_ROOT / "working" / "resume_ats_build.html")

CONTACT = {
    "name":  _cfg.get("name", "Your Full Name"),
    "line":  (
        f'{_cfg.get("location", "City, ST")}  |  '
        f'{_cfg.get("phone", "(555) 555-5555")}  |  '
        f'{_cfg.get("email", "you@example.com")}  |  '
        f'{_cfg.get("linkedin_display", "linkedin.com/in/yourprofile")}'
    ),
}

# Replace this with your own skill set. Override per role by adding a "skills"
# object to resume_content.json.
DEFAULT_SKILLS = {
    "Healthcare Integration": ["HL7 (v2/v3)", "DICOM", "Interface Engine",
        "Epic Integration", "Cerner Integration", "REST API", "SOAP", "XML / XSLT",
        "JSON", "CSV", "SFTP"],
    "Data & Databases": ["SQL Server", "ETL Pipelines",
        "Database Migration & Mapping", "Data Validation & Reconciliation"],
    "Programming & Scripting": ["Python", "SQL", "PowerShell"],
    "Platforms & Infrastructure": ["Linux Server Administration",
        "Azure (VMs)", "VPN / TCP-IP"],
    "Security & Compliance": ["HIPAA Compliance", "MFA Configuration"],
    "Delivery": ["Requirements & Discovery", "UAT", "Go-Live",
        "Stakeholder Management", "Implementation Process Design"],
    "AI Tools": ["Claude", "Claude Code", "OpenCode", "Gemini"],
}

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Calibri','Arial',sans-serif; font-size:10.5pt; color:#000;
       background:#fff; padding:0.45in 0.7in; line-height:1.26; }
h1 { font-size:19pt; letter-spacing:0.3px; }
.contact { font-size:10pt; color:#222; margin:2px 0 8px; }
h2 { font-size:11.5pt; text-transform:uppercase; letter-spacing:0.6px;
     border-bottom:1.2px solid #000; padding-bottom:2px; margin:10px 0 5px;
     break-after:avoid; page-break-after:avoid; }
p.summary { margin-bottom:3px; }
.skillgroup { margin-bottom:1px; }
.role { margin-top:5px; break-inside:avoid; page-break-inside:avoid; }
.role .titleline { font-weight:bold; font-size:11pt; }
.role .meta { font-style:italic; color:#222; font-size:10pt; margin-bottom:2px; }
.role .note { font-size:10pt; margin:1px 0 3px; }
ul { margin:0 0 1px 17px; }
li { margin-bottom:1.5px; }
.proj .titleline { font-weight:bold; font-size:11pt; }
.proj .meta { font-style:italic; color:#222; font-size:10pt; margin-bottom:2px; }
.cert { margin-bottom:2px; break-inside:avoid; page-break-inside:avoid; }
.cert b { font-size:10.5pt; }
.cert span { color:#222; font-size:10pt; }
@media print { @page { size:letter; margin:0; } }
"""


def esc(s): return html.escape(str(s))


def render_skills(skills):
    if isinstance(skills, list):
        return f'<p>{esc(", ".join(skills))}</p>'
    out = ""
    for group, items in skills.items():
        out += f'<div class="skillgroup"><b>{esc(group)}:</b> {esc(", ".join(items))}</div>\n'
    return out


def build_html(c):
    skills = c.get("skills") or DEFAULT_SKILLS

    parts = [f'<h1>{esc(CONTACT["name"])}</h1>',
             f'<div class="contact">{esc(CONTACT["line"])}</div>']

    parts.append('<h2>Summary</h2>')
    for para in c["summary"]:
        parts.append(f'<p class="summary">{esc(para)}</p>')

    parts.append('<h2>Core Skills</h2>')
    parts.append(render_skills(skills))

    if c.get("key_project"):
        proj = c["key_project"]
        title = proj["title"].replace("▸", "").strip()
        parts.append('<h2>Key Project</h2>')
        parts.append('<div class="proj">')
        parts.append(f'<div class="titleline">{esc(title)}</div>')
        if proj.get("subtitle"):
            parts.append(f'<div class="meta">{esc(proj["subtitle"].replace("·", "|"))}</div>')
        parts.append('<ul>')
        for b in proj["bullets"]:
            parts.append(f'<li>{esc(b)}</li>')
        parts.append('</ul></div>')

    parts.append('<h2>Professional Experience</h2>')
    for role in c["experience"]:
        parts.append('<div class="role">')
        parts.append(f'<div class="titleline">{esc(role["title"])}</div>')
        parts.append(f'<div class="meta">{esc(role["company"])} &nbsp;—&nbsp; {esc(role["dates"])}</div>')
        if role.get("transition_note"):
            parts.append(f'<div class="note">{esc(role["transition_note"])}</div>')
        parts.append('<ul>')
        for b in role["bullets"]:
            parts.append(f'<li>{esc(b)}</li>')
        parts.append('</ul></div>')

    if c.get("education"):
        parts.append('<h2>Certifications &amp; Professional Development</h2>')
        for item in c["education"]:
            sub = f' <span>— {esc(item["sub"])}</span>' if item.get("sub") else ""
            parts.append(f'<div class="cert"><b>{esc(item["title"])}</b>{sub}</div>')

    body = "\n".join(parts)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<style>{CSS}</style></head><body>{body}</body></html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: resume_builder_ats.py <path_to_resume_content.json>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        c = json.load(f)

    company = c["company"]
    out_dir = JOBHUNT / company
    pdf_out = str(out_dir / f"{NAME_SLUG}-Resume.pdf")
    os.makedirs(out_dir, exist_ok=True)

    (REPO_ROOT / "working").mkdir(parents=True, exist_ok=True)
    with open(HTMLOUT, "w", encoding="utf-8") as f:
        f.write(build_html(c))

    file_url = "file:///" + HTMLOUT.replace("\\", "/")
    subprocess.run([EDGE, "--headless", "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_out}", "--print-to-pdf-no-header", "--no-margins",
        file_url], capture_output=True, text=True, timeout=40)

    if os.path.exists(pdf_out):
        print(f"ATS PDF: {pdf_out}  ({os.path.getsize(pdf_out)//1024} KB)")
    else:
        print("ERROR: ATS PDF not created"); sys.exit(1)


if __name__ == "__main__":
    main()

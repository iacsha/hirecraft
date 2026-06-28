r"""
cover_letter_builder.py — Generate cover letter PDFs.

Usage:
    python cover_letter_builder.py <company> [position]

Reads:
    <jobhunt_root>\<company>\cover_letter_draft.txt
    (falls back to working\cover_letter_draft.txt)

The draft file must follow this structure:
  Line 1:    Your Name         (stripped — header is added by template)
  Line 2:    contact line      (stripped — added by template)
  Line 3:    blank
  Line 4:    date
  Line 5:    addressee / company
  Line 6:    blank
  Line 7:    salutation
  Line 8+:   body paragraphs + closing

Header (name / email / LinkedIn) is templated from config.json.
Email and LinkedIn render as clickable links.

Generates styled HTML and prints to PDF via Microsoft Edge headless.

SETUP
-----
Copy config.example.json to config.json and fill in your details.

OUTPUT
------
  <jobhunt_root>\<company>\<name_slug>-Cover-Letter.pdf

DESIGN
------
  - Dark header: name (13pt bold) + contact (9.5pt) + teal divider
  - Body: Arial 11pt, 1.55 line-height, 0.75in/1.0in margins
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


_cfg      = load_config()
NAME_SLUG = _cfg.get("name_slug", "Your-Name")
JOBHUNT   = Path(_cfg.get("jobhunt_root", str(REPO_ROOT.parent)))
HTML_WORK = str(REPO_ROOT / "working" / "cover_letter_build.html")
DRAFT_FALLBACK = str(REPO_ROOT / "working" / "cover_letter_draft.txt")

_name     = _cfg.get("name", "Your Full Name")
_email    = _cfg.get("email", "you@example.com")
_phone    = _cfg.get("phone", "(555) 555-5555")
_linkedin_url  = _cfg.get("linkedin_url", "https://www.linkedin.com/in/yourprofile")
_linkedin_disp = _cfg.get("linkedin_display", "linkedin.com/in/yourprofile")

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family:Arial,Calibri,sans-serif;
  font-size:11pt; color:#1a1a1a; background:#fff;
  padding:0.75in 1.0in; line-height:1.55;
}
.header h1 {
  font-size:14pt; font-weight:700; color:#1a1a1a;
  letter-spacing:0.4px; line-height:1.1;
}
.header .contact {
  font-size:9.5pt; color:#555; margin-top:3px;
}
.header .contact a { color:#1A9E8F; text-decoration:none; }
.divider {
  border:none; border-top:2px solid #1A9E8F; margin:8px 0 20px;
}
p { margin-bottom:13px; font-size:11pt; }
.closing { margin-top:20px; }
.closing-line { margin-bottom:26px; }
.sig { font-size:11.5pt; font-weight:700; }
@media print {
  body { padding:0.65in 0.9in; }
  @page { size:letter; margin:0; }
}
"""

HEADER_HTML = f"""
<div class="header">
  <h1>{html.escape(_name)}</h1>
  <div class="contact">
    <a href="mailto:{html.escape(_email)}">{html.escape(_email)}</a>
    &nbsp;|&nbsp; {html.escape(_phone)}
    &nbsp;|&nbsp; <a href="{html.escape(_linkedin_url)}">{html.escape(_linkedin_disp)}</a>
  </div>
</div>
<hr class="divider">
"""


def drop_redundant_addressee(blocks):
    """Drop a standalone addressee line when it just duplicates the salutation.

    e.g. "Acme Hiring Team" immediately followed by "Dear Acme Hiring Team,"
    is redundant — keep only the salutation. A real inside-address (different
    text, e.g. a person + street) is left untouched.
    """
    sal_idx = next((i for i, b in enumerate(blocks)
                    if b.lower().startswith("dear ")), None)
    if sal_idx is None or sal_idx == 0:
        return blocks
    sal_core = blocks[sal_idx][len("Dear "):].rstrip(",:").strip().lower()
    addr = blocks[sal_idx - 1].rstrip(",:").strip().lower()
    if addr == sal_core:
        return blocks[:sal_idx - 1] + blocks[sal_idx:]
    return blocks


def build_html(body_lines):
    blocks = [ln.strip() for ln in body_lines if ln.strip()]
    blocks = drop_redundant_addressee(blocks)
    body_html = ""
    for b in blocks:
        body_html += f"<p>{html.escape(b)}</p>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{CSS}</style>
</head>
<body>
{HEADER_HTML}
{body_html}
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: cover_letter_builder.py <company> [position]")
        sys.exit(1)

    company  = sys.argv[1]
    out_dir  = JOBHUNT / company
    pdf_out  = str(out_dir / f"{NAME_SLUG}-Cover-Letter.pdf")
    os.makedirs(out_dir, exist_ok=True)

    company_draft = str(JOBHUNT / company / "cover_letter_draft.txt")
    draft_path = company_draft if os.path.exists(company_draft) else DRAFT_FALLBACK
    with open(draft_path, encoding="utf-8") as f:
        lines = f.readlines()

    body_lines = lines[3:]  # skip name line, contact line, blank line

    (REPO_ROOT / "working").mkdir(parents=True, exist_ok=True)
    html_content = build_html(body_lines)
    with open(HTML_WORK, "w", encoding="utf-8") as f:
        f.write(html_content)

    file_url = "file:///" + HTML_WORK.replace("\\", "/")
    result = subprocess.run([
        EDGE, "--headless", "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_out}",
        "--print-to-pdf-no-header", "--no-margins",
        file_url
    ], capture_output=True, text=True, timeout=30)

    if os.path.exists(pdf_out):
        kb = os.path.getsize(pdf_out) // 1024
        print(f"PDF:  {pdf_out}  ({kb} KB)")
    else:
        print("ERROR: PDF not created")
        print(result.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

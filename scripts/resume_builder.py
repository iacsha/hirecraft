r"""
resume_builder.py — Generate tailored two-column resume PDFs.

Usage:
    python resume_builder.py <path_to_resume_content.json>

Reads resume_content.json, clones your master DOCX template, replaces the
left column with tailored content using lxml, repacks as DOCX, and exports
to PDF via Word COM (Windows only).

The right sidebar (technical skills + contact) is preserved unchanged from
the master template — only the left column (summary, experience, key project,
education) is replaced.

SETUP
-----
Copy config.example.json to config.json and fill in your details.

  jobhunt_root    — folder where per-company application folders will be created
  resume_template — filename of your master DOCX template (in jobhunt_root\root\)
  name_slug       — used in output filenames, e.g. "Jane-Smith"

OUTPUT
------
  <jobhunt_root>\<company>\<name_slug>-Resume-Designed.docx
  <jobhunt_root>\<company>\<name_slug>-Resume-Designed.pdf

RESUME CONTENT JSON SCHEMA
---------------------------
{
  "company":   "CompanyName",
  "position":  "Role Title",
  "summary":   ["paragraph 1", "paragraph 2"],
  "experience": [
    {
      "title":   "Role Title",
      "company": "Employer Name",
      "dates":   "Jan 2020 – Present",
      "keep_together": false,
      "bullets": ["bullet text", ...]
    }
  ],
  "key_project": {
    "title":    "Project Name  —  Subtitle",
    "subtitle": "role  duration  context",
    "bullets":  ["bullet text", ...]
  },
  "education": [
    {"title": "Cert Name  —  Certified (Year)", "sub": "Issuer  Context"}
  ]
}

PAGINATION
----------
- Target is <=2 pages; the script prints a WARNING if exceeded.
- Role titles use keepNext so a heading never orphans at the bottom of a page.
- Bullets use keepLines so a single bullet never wraps across a page break.
- To force a role to START on a fresh page, set "keep_together": true on that
  role. This glues the whole role block into one keepNext chain that Word moves
  to the next page as a unit. pageBreakBefore does NOT work inside table cells.
"""

import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree as ET
import win32com.client

# ── CONFIG ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parent
CONFIG_PATH = REPO_ROOT / "config.json"


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else REPO_ROOT / "config.example.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_cfg        = load_config()
NAME_SLUG   = _cfg.get("name_slug", "Your-Name")
JOBHUNT     = Path(_cfg.get("jobhunt_root", str(REPO_ROOT.parent)))
TEMPLATE    = JOBHUNT / "root" / _cfg.get("resume_template", "YourName_Resume.docx")
WORK        = REPO_ROOT / "working" / "resume_build"

# ── XML NAMESPACE ─────────────────────────────────────────────────────────────
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XNS = "http://www.w3.org/XML/1998/namespace"

def w(tag):  return f"{{{WNS}}}{tag}"
def x(attr): return f"{{{XNS}}}{attr}"

# ── RUN PROPERTY BUILDERS ─────────────────────────────────────────────────────
def _fonts(parent):
    el = ET.SubElement(parent, w("rFonts"))
    for a in ["ascii", "cs", "eastAsia", "hAnsi"]:
        el.set(w(a), "Arial")

def _rpr(color, sz, bold=False, italic=False):
    rpr = ET.Element(w("rPr"))
    _fonts(rpr)
    if bold:   ET.SubElement(rpr, w("b"));  ET.SubElement(rpr, w("bCs"))
    if italic: ET.SubElement(rpr, w("i"));  ET.SubElement(rpr, w("iCs"))
    ET.SubElement(rpr, w("color")).set(w("val"), color)
    ET.SubElement(rpr, w("sz")).set(w("val"),    str(sz))
    ET.SubElement(rpr, w("szCs")).set(w("val"),  str(sz))
    return rpr

def _run(color, sz, text, bold=False, italic=False):
    r = ET.Element(w("r"))
    r.append(_rpr(color, sz, bold, italic))
    t = ET.SubElement(r, w("t"))
    t.set(x("space"), "preserve")
    t.text = text
    return r

def _ppr(after=None, before=None, border_bottom=False,
         style=None, numId=None, keep_next=False, keep_lines=False,
         page_break=False):
    # Child elements must follow the OOXML CT_PPr schema sequence or Word
    # silently drops misplaced ones. Order: pStyle → keepNext → keepLines →
    # pageBreakBefore → numPr → pBdr → spacing
    pPr = ET.Element(w("pPr"))
    if style:
        ET.SubElement(pPr, w("pStyle")).set(w("val"), style)
    if keep_next:  ET.SubElement(pPr, w("keepNext"))
    if keep_lines: ET.SubElement(pPr, w("keepLines"))
    if page_break: ET.SubElement(pPr, w("pageBreakBefore"))
    if numId is not None:
        numPr = ET.SubElement(pPr, w("numPr"))
        ET.SubElement(numPr, w("ilvl")).set(w("val"), "0")
        ET.SubElement(numPr, w("numId")).set(w("val"), str(numId))
    if border_bottom:
        pBdr = ET.SubElement(pPr, w("pBdr"))
        bot  = ET.SubElement(pBdr, w("bottom"))
        bot.set(w("val"), "single"); bot.set(w("color"), "1A9E8F")
        bot.set(w("sz"), "10");      bot.set(w("space"), "3")
    sp = ET.SubElement(pPr, w("spacing"))
    if after  is not None: sp.set(w("after"),  str(after))
    if before is not None: sp.set(w("before"), str(before))
    return pPr

# ── PARAGRAPH CONSTRUCTORS ────────────────────────────────────────────────────
# Colors:  1A9E8F = teal section header
#          0D2B45 = dark navy role/cert titles
#          3E5668 = slate company name
#          8A9BAD = gray dates / cert subtitle
#          333333 = dark gray body text
#          222222 = near-black bullet text

def p_section(label, before=260):
    """Teal section header with bottom border.
    No keep_next here — keepNext on the first cell paragraph pushes the entire
    body row to the next page, stranding the header band alone on page 1."""
    p = ET.Element(w("p"))
    p.append(_ppr(after=120, before=before, border_bottom=True))
    p.append(_run("1A9E8F", 20, label, bold=True))
    return p

def p_body(text, after=200, before=0):
    p = ET.Element(w("p"))
    p.append(_ppr(after=after, before=before))
    p.append(_run("333333", 18, text))
    return p

def p_role(title):
    p = ET.Element(w("p"))
    p.append(_ppr(after=40, before=120, keep_next=True))
    p.append(_run("0D2B45", 22, title, bold=True))
    return p

def p_company(company, dates):
    p = ET.Element(w("p"))
    p.append(_ppr(after=80, before=0, keep_next=True))
    p.append(_run("3E5668", 18, company, italic=True))
    p.append(_run("8A9BAD", 17, f"   {dates}"))
    return p

def p_bullet(text, keep_next=False):
    p = ET.Element(w("p"))
    p.append(_ppr(after=52, before=0, style="ListParagraph", numId=2,
                  keep_lines=True, keep_next=keep_next))
    p.append(_run("222222", 18, text))
    return p

def p_project_title(text):
    p = ET.Element(w("p"))
    p.append(_ppr(after=30, before=140, keep_next=True))
    p.append(_run("0D2B45", 19, text, bold=True))
    return p

def p_project_sub(text):
    p = ET.Element(w("p"))
    p.append(_ppr(after=60, before=0, keep_next=True))
    p.append(_run("8A9BAD", 17, text, italic=True))
    return p

def p_cert_title(text):
    p = ET.Element(w("p"))
    p.append(_ppr(after=30, before=100, keep_next=True))
    p.append(_run("0D2B45", 19, text, bold=True))
    return p

def p_cert_sub(text):
    p = ET.Element(w("p"))
    p.append(_ppr(after=80, before=0))
    p.append(_run("8A9BAD", 17, text, italic=True))
    return p

# ── CONTENT BUILDER ───────────────────────────────────────────────────────────
def build_left_column(content):
    ps = []

    ps.append(p_section("SUMMARY", before=0))
    for i, para in enumerate(content["summary"]):
        after = 80 if i < len(content["summary"]) - 1 else 200
        ps.append(p_body(para, after=after))

    ps.append(p_section("EXPERIENCE"))
    for role in content["experience"]:
        # "keep_together": true glues the whole role block (title + company +
        # every bullet) via a keepNext chain. Word moves the entire role to the
        # next page rather than splitting it. pageBreakBefore is ignored inside
        # table cells — keep_together is the correct mechanism for this layout.
        keep = role.get("keep_together", False)
        ps.append(p_role(role["title"]))
        ps.append(p_company(role["company"], role["dates"]))
        if role.get("transition_note"):
            ps.append(p_body(role["transition_note"], after=120, before=0))
        bullets = role["bullets"]
        for i, bullet in enumerate(bullets):
            chain = keep and (i < len(bullets) - 1)
            ps.append(p_bullet(bullet, keep_next=chain))

    if "key_project" in content:
        proj = content["key_project"]
        ps.append(p_section("KEY PROJECT"))
        ps.append(p_project_title(proj["title"]))
        if proj.get("subtitle"):
            ps.append(p_project_sub(proj["subtitle"]))
        for bullet in proj["bullets"]:
            ps.append(p_bullet(bullet))

    if content.get("education"):
        ps.append(p_section("EDUCATION & TRAINING"))
        for item in content["education"]:
            ps.append(p_cert_title(item["title"]))
            if item.get("sub"):
                ps.append(p_cert_sub(item["sub"]))

    return ps

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    content_path = sys.argv[1] if len(sys.argv) > 1 \
        else str(REPO_ROOT / "working" / "resume_content.json")

    with open(content_path, encoding="utf-8") as f:
        content = json.load(f)

    company  = content["company"]
    out_dir  = JOBHUNT / company
    docx_out = str(out_dir / f"{NAME_SLUG}-Resume-Designed.docx")
    pdf_out  = str(out_dir / f"{NAME_SLUG}-Resume-Designed.pdf")

    os.makedirs(out_dir, exist_ok=True)
    if WORK.exists(): shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    with zipfile.ZipFile(TEMPLATE, 'r') as z:
        z.extractall(WORK)

    doc_path = WORK / "word" / "document.xml"
    parser   = ET.XMLParser(remove_blank_text=False, recover=True)
    tree     = ET.parse(str(doc_path), parser)
    root     = tree.getroot()

    body      = root.find(w("body"))
    body_tbl  = body.findall(w("tbl"))[1]
    left_cell = body_tbl.find(w("tr")).findall(w("tc"))[0]

    for child in list(left_cell):
        if child.tag != w("tcPr"):
            left_cell.remove(child)

    for p in build_left_column(content):
        left_cell.append(p)

    tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8",
               standalone=True, pretty_print=False)

    if os.path.exists(docx_out): os.remove(docx_out)
    with zipfile.ZipFile(docx_out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for dirpath, _, files in os.walk(WORK):
            for fname in files:
                fp = os.path.join(dirpath, fname)
                zout.write(fp, os.path.relpath(fp, WORK))
    print(f"DOCX: {docx_out}")

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(docx_out)
        page_count = doc.ComputeStatistics(2)
        doc.SaveAs(pdf_out, FileFormat=17)
        doc.Close(False)
        print(f"PDF:  {pdf_out}")
        if page_count > 2:
            print(f"\nWARNING: Resume is {page_count} pages. Target is <=2 pages.")
            print("  Reduce bullet counts in resume_content.json and regenerate.")
        else:
            print(f"OK: {page_count} page(s) — within 2-page limit")
    finally:
        word.Quit()


if __name__ == "__main__":
    main()

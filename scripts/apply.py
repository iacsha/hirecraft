#!/usr/bin/env python3
"""
apply.py — Unified pipeline for generating job application PDFs.

Usage:
  python apply.py Cedar                    Build resume + cover letter for Cedar
  python apply.py Cedar --resume-only      Resume only
  python apply.py Cedar --cover-only       Cover letter only
  python apply.py Cedar --open             Build and open PDFs
  python apply.py Cedar --ats              Build + also generate ATS resume (no prompt)
  python apply.py Cedar --no-ats           Build, skip ATS resume (no prompt)
  python apply.py --list                   List all companies with application folders
  python apply.py --init CompanyName <JD URL>  Create new company folder structure

If neither --ats nor --no-ats is given, you'll be prompted whether to also
generate the ATS-safe (single-column, keyword-skills) resume for portal uploads.

SETUP
-----
Copy config.example.json to config.json and fill in your details.
Set jobhunt_root to the folder where per-company application folders will live.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parent
CONFIG_PATH = REPO_ROOT / "config.json"

RESUME_BUILDER = SCRIPT_DIR / "resume_builder.py"
ATS_BUILDER    = SCRIPT_DIR / "resume_builder_ats.py"
COVER_BUILDER  = SCRIPT_DIR / "cover_letter_builder.py"


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else REPO_ROOT / "config.example.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_cfg         = load_config()
NAME_SLUG    = _cfg.get("name_slug", "Your-Name")
JOBHUNT_ROOT = Path(_cfg.get("jobhunt_root", str(REPO_ROOT.parent)))


def list_companies():
    folders = []
    for p in sorted(JOBHUNT_ROOT.iterdir()):
        if p.is_dir() and (p / "resume_content.json").exists():
            folders.append(p.name)
    if not folders:
        print("No company application folders found.")
        return
    print("Application folders found:")
    for f in folders:
        has_cover = "Y" if (JOBHUNT_ROOT / f / "cover_letter_draft.txt").exists() else "-"
        has_job   = "Y" if (JOBHUNT_ROOT / f / "job_posting.json").exists() else "-"
        has_gap   = "Y" if (JOBHUNT_ROOT / f / "gap_analysis.json").exists() else "-"
        print(f"  {f}  [job{has_job}] [gap{has_gap}] [cover{has_cover}]")


def init_company(name, jd_url=""):
    path = JOBHUNT_ROOT / name
    if path.exists():
        print(f"Folder already exists: {path}")
        return False
    path.mkdir(parents=True)
    job_file = path / "job_posting.json"
    job_data = {
        "company": name,
        "position": "",
        "posting_url": jd_url,
        "date_found": "",
        "source": "LinkedIn",
        "salary_range": "",
        "location": "",
        "remote_type": "",
        "requirements": {"required": [], "preferred": [], "education": [], "experience_years": 0},
        "responsibilities": [],
        "company_description": ""
    }
    with open(job_file, "w", encoding="utf-8") as f:
        json.dump(job_data, f, indent=2)
    print(f"Created {job_file}")
    print(f"  Edit this file with JD details, then create resume_content.json.")
    return True


def validate_company(name):
    path = JOBHUNT_ROOT / name
    errors = []
    if not path.exists():
        errors.append(f"Folder not found: {path}")
    content_file = path / "resume_content.json"
    if not content_file.exists():
        errors.append(f"Missing: {content_file}")
    else:
        try:
            with open(content_file, encoding="utf-8") as f:
                data = json.load(f)
            for key in ["company", "position", "summary", "experience"]:
                if key not in data:
                    errors.append(f"resume_content.json missing key: '{key}'")
            if len(data.get("experience", [])) == 0:
                errors.append("resume_content.json has no experience entries")
        except json.JSONDecodeError as e:
            errors.append(f"resume_content.json invalid JSON: {e}")
    return errors


def build(name, resume_only=False, cover_only=False, open_pdfs=False, ats_flag=None):
    print(f"\n{'=' * 60}")
    print(f"  APPLY — {name}")
    print(f"{'=' * 60}")

    errors = validate_company(name)
    if errors:
        for e in errors:
            print(f"  [X] {e}")
        print("  Fix errors and try again.")
        sys.exit(1)

    path         = JOBHUNT_ROOT / name
    content_file = path / "resume_content.json"
    cover_file   = path / "cover_letter_draft.txt"
    pdfs = []

    if not cover_only:
        print(f"\n  [1/2] Building resume PDF...")
        result = subprocess.run(
            [sys.executable, str(RESUME_BUILDER), str(content_file)],
            capture_output=True, text=True, cwd=str(JOBHUNT_ROOT)
        )
        print("  " + result.stdout.strip().replace("\n", "\n  "))
        if result.returncode != 0:
            print(f"  [X] Resume build failed:\n  " + result.stderr.strip().replace("\n", "\n  "))
            sys.exit(1)
        pdf = path / f"{NAME_SLUG}-Resume-Designed.pdf"
        if pdf.exists():
            pdfs.append(pdf)

        make_ats = ats_flag
        if make_ats is None:
            try:
                ans = input("\n  Also generate ATS-safe (single-column) resume for portal uploads? [Y/n]: ").strip().lower()
            except EOFError:
                ans = "y"
            make_ats = ans in ("", "y", "yes")
        if make_ats:
            print(f"  Building ATS-safe resume PDF...")
            result = subprocess.run(
                [sys.executable, str(ATS_BUILDER), str(content_file)],
                capture_output=True, text=True, cwd=str(JOBHUNT_ROOT)
            )
            print("  " + result.stdout.strip().replace("\n", "\n  "))
            if result.returncode == 0:
                ats_pdf = path / f"{NAME_SLUG}-Resume.pdf"
                if ats_pdf.exists():
                    pdfs.append(ats_pdf)
            else:
                print(f"  [X] ATS resume build failed:\n  " + result.stderr.strip().replace("\n", "\n  "))

    if not resume_only:
        if cover_file.exists():
            print(f"  [2/2] Building cover letter PDF...")
            result = subprocess.run(
                [sys.executable, str(COVER_BUILDER), name],
                capture_output=True, text=True, cwd=str(JOBHUNT_ROOT)
            )
            print("  " + result.stdout.strip().replace("\n", "\n  "))
            if result.returncode != 0:
                print(f"  [X] Cover letter build failed:\n  " + result.stderr.strip().replace("\n", "\n  "))
                sys.exit(1)
            pdf = path / f"{NAME_SLUG}-Cover-Letter.pdf"
            if pdf.exists():
                pdfs.append(pdf)
        else:
            print(f"  [2/2] No cover_letter_draft.txt found — skipping.")

    print(f"\n{'=' * 60}")
    print(f"  BUILD COMPLETE")
    for p in pdfs:
        size = p.stat().st_size
        print(f"    {p.name}  ({size // 1024} KB)")
    print(f"{'=' * 60}")

    if open_pdfs and pdfs:
        print("  Opening PDFs...")
        for p in pdfs:
            os.startfile(str(p))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "--list":
        list_companies()
        return

    if cmd == "--init":
        if len(sys.argv) < 3:
            print("Usage: python apply.py --init CompanyName [JD_URL]")
            return
        init_company(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        return

    name  = cmd
    flags = set(sys.argv[2:])
    ats_flag = None
    if "--ats" in flags:
        ats_flag = True
    elif "--no-ats" in flags:
        ats_flag = False
    build(
        name,
        resume_only="--resume-only" in flags,
        cover_only="--cover-only" in flags,
        open_pdfs="--open" in flags,
        ats_flag=ats_flag,
    )


if __name__ == "__main__":
    main()

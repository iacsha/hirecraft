# HireCraft

**AI-powered job application toolkit.** Tailored resume PDFs, ATS-safe exports, cover letters, and recruiter icebreakers, all driven by a single master resume and a Claude Code slash command.

Built and used during a real healthcare IT job search. Every script here earned its place.

---

## What It Does

You paste a job description. HireCraft handles the rest:

- Parses the posting and scores your fit against your master resume
- Writes a tailored resume (two-column designed PDF + single-column ATS PDF)
- Drafts a cover letter in your voice
- Generates recruiter icebreaker options based on real commonalities
- Tracks the application in your folder structure

One command. One consistent output format. No manual copy-paste between tools.

---

## How It Works With career-ops

HireCraft pairs with **[career-ops](https://github.com/santifer/career-ops)** by santifer.

- **career-ops**: discovers, evaluates, and scores job postings from portals (Greenhouse, Ashby, Lever, Workday). Feeds you leads.
- **HireCraft**: executes the application once you decide to apply. Builds the documents, tracks the output, drafts the outreach.

Use career-ops to find and filter. Use HireCraft to act.

---

## Prerequisites

- Python 3.10+
- Windows (resume_builder.py uses Word COM for PDF export; cover_letter_builder.py and resume_builder_ats.py use Microsoft Edge headless)
- Microsoft Word installed
- Microsoft Edge installed
- A master DOCX resume template (two-column layout where the right sidebar stays fixed and the left column gets replaced per role)
- [Claude Code](https://claude.ai/code) for the `/process-job` slash command pipeline

Install Python dependencies:
```
pip install -r requirements.txt
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/iacsha/hirecraft.git
cd hirecraft
```

**2. Configure**
```bash
cp config.example.json config.json
```
Edit `config.json` with your name, contact info, and paths.

**3. Set up your master resume**
```bash
cp master_resume.example.json master_resume.json
```
Fill in your real experience, skills, certifications, and interests. This is your single source of truth; all scripts read from it.

**4. Add your resume template**

Place your two-column DOCX template in your `jobhunt_root` folder and set `resume_template` in `config.json` to match the filename.

---

## Usage

### Interactive wizard (recommended starting point)

```bash
python scripts/wizard.py
```

A terminal menu that walks through the full pipeline: job processing, gap analysis, skill comfort ratings, document builds, recruiter icebreaker, interview prep, and application tracking. Works without Claude Code installed; it prints AI prompts for manual use when the CLI is not available.

### Slash command (Claude Code)

From Claude Code, inside this folder:

```
/process-job
```

Paste a job description. The pipeline walks through parsing, gap analysis, cover letter, resume generation, and output saving.

### Scripts directly

```bash
# Full build (resume + cover letter)
python scripts/apply.py CompanyName

# Resume only
python scripts/apply.py CompanyName --resume-only

# ATS-safe resume only
python scripts/apply.py CompanyName --ats

# Generate recruiter icebreaker
python scripts/linkedin_icebreaker.py recruiter_profile.txt

# List all application folders
python scripts/apply.py --list

# Initialize a new company folder
python scripts/apply.py --init CompanyName https://posting-url
```

---

## Folder Structure

```
hirecraft/
├── config.example.json              # Copy to config.json and fill in
├── master_resume.example.json       # Copy to master_resume.json and fill in
├── HONESTY.md                       # The no-fabrication system and apply-direct guidance
├── WORKFLOW.md                      # End-to-end pipeline diagrams
├── scripts/
│   ├── wizard.py                    # Interactive terminal wizard (start here)
│   ├── apply.py                     # Unified pipeline CLI
│   ├── resume_builder.py            # Two-column designed resume (DOCX + PDF)
│   ├── resume_builder_ats.py        # Single-column ATS-safe resume (PDF)
│   ├── cover_letter_builder.py      # Cover letter PDF
│   └── linkedin_icebreaker.py       # Recruiter outreach generator
├── templates/
│   └── answer-bank.example.md       # Reusable answers to recurring screening questions
├── obsidian/
│   └── company-note-template.md     # Obsidian note template for tracking applications
└── .claude/
    └── commands/
        ├── process-job.md           # /process-job slash command
        ├── build-master-resume.md   # /build-master-resume slash command
        └── build-job-history.md     # /build-job-history slash command
```

Per-company output (gitignored) lives in your `jobhunt_root`:
```
<jobhunt_root>/CompanyName/
├── YourName-Resume-Designed.pdf
├── YourName-Resume-Designed.docx
├── YourName-Resume.pdf           # ATS version
├── YourName-Cover-Letter.pdf
├── resume_content.json
├── cover_letter_draft.txt
├── job_posting.json
└── gap_analysis.json
```

---

## Acknowledgments

HireCraft was built alongside some excellent tools. Credit where it's due:

- **[career-ops](https://github.com/santifer/career-ops)** by [santifer](https://santifer.io): the job pipeline engine that feeds this toolkit leads. If you're not using it, start there first.
- **[Claude Code](https://claude.ai/code)**: AI review, resume drafting, and the `/process-job` pipeline backbone.
- **[OpenCode](https://opencode.ai)**: AI-assisted first-draft generation throughout the search.
- **[Gemini CLI](https://github.com/google-gemini/gemini-cli)**: supplemental research and cross-checking.
- **[Obsidian](https://obsidian.md)**: application tracking vault that sits alongside this toolkit.

---

## License

MIT

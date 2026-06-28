# Process Job

Process a job posting through the full pipeline.

Usage:
- `/process-job <url>` — fetch the posting from the URL
- `/process-job` + pasted job text — parse the text directly (preferred)

> **READ FIRST:** `REFERENCE.md` in this repo — index of every reusable file
> (scripts, master resume, template, output naming) plus your standing honesty
> constraints. Read it before exploring the repo to save tokens.

## Step 1 — Parse Job Posting

Accept either input form:

- **Pasted text (preferred):** If the command includes the posting text (not just
  a URL), parse it directly. Do NOT call WebFetch — the text is already complete
  and accurate. This avoids login walls and fetch failures.
- **URL only:** If only a URL is given, call WebFetch once. If the fetch returns a
  login wall, partial content, or error, STOP and ask the user to paste the text.
  Do not retry repeatedly.

Extract all available information into a structured object:

```json
{
  "company": "",
  "position": "",
  "posting_url": "",
  "date_found": "",
  "source": "",
  "salary_range": null,
  "location": "",
  "remote_type": "",
  "apply_url": "",
  "requirements": {
    "required": [],
    "preferred": [],
    "education": [],
    "experience_years": null
  },
  "responsibilities": [],
  "benefits": [],
  "company_description": "",
  "raw_text": ""
}
```

Save to: `working/job_posting.json`

## Step 2 — Latent Skills Check

Load `master_resume.json` and `job_history.json`.

Identify skills in the posting's `required` and `preferred` arrays that:
- Do NOT exist in master_resume skills (technical, tools, soft, or latent_skills)
- Are NOT already in job_history pattern_analysis.common_gaps with comfort_level recorded

For each unknown skill found, ask interactively (max 2 skills per batch):

```
Found skill in posting not in your profile: "[SKILL NAME]"
Context from posting: "[exact line from JD where it appears]"
Comfort level?
  [0/1] None / Aware
  [2] Some hands-on — homelab, side projects, limited production
  [3] Comfortable — used it regularly
  [4] Strong — deep experience, could teach it
```

After answers, ask for brief context on any skill rated 2+.

Save all answers to master_resume.json under `latent_skills`:
```json
{
  "name": "",
  "comfort_level": "",
  "comfort_score": 0,
  "context": "",
  "tags": [],
  "first_seen_at": "",
  "added": ""
}
```

Comfort level 0/1 — record it so we never ask again, exclude from scoring.

## Step 3 — Gap Analysis

Compare job_posting.json against master_resume.json (including latent_skills)
and job_history.json pattern_analysis.

Score the match out of 100:
- Required skills match: 50 points
- Preferred skills match: 20 points
- Domain/experience match: 15 points
- Years of experience match: 10 points
- Salary within target: 5 points (0 if below target or unknown)

Deduct points for:
- Known recurring gaps (from pattern_analysis.common_gaps): -5 each, max -15
- Hard requirements not met (certs, specific platforms): -10 each

For each gap identified, flag as:
- `known_recurring` — already in pattern_analysis.common_gaps
- `new_gap` — first time seeing this requirement
- `latent_partial` — in latent_skills with comfort_score 2+
- `hard_blocker` — required, no experience at any level

Save to: `working/gap_analysis.json`

Print summary:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 [COMPANY] — [POSITION]
 Score: XX/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ✅ Strong matches: X
 ⚠  Known recurring gaps: X
 🔴 Hard blockers: X
 💰 Salary: $XX,XXX - $XX,XXX [ABOVE/BELOW/UNKNOWN target]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2-3 sentence honest assessment]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Step 4 — Cover Letter Prompt

Ask: Generate cover letter? [Yes / No]

## Step 5 — Apply or Pass

Ask: Apply or pass?

If pass — skip to Step 9 (Obsidian/notes file only, no resume/cover letter generated).

## Step 6 — Resume Writer (if applying)

Using master_resume.json, gap_analysis.json, and job_posting.json, write the
tailored resume content and save it as structured JSON.

### Rules
- Lead with the strongest matching bullets for this specific role
- Reframe bullets where appropriate to mirror JD language without fabricating
- For latent_skills with comfort_score 2+, weave into skills section naturally
- For known recurring gaps — do NOT fabricate; minimize or omit
- For hard blockers — do NOT mention at all
- Keep summary tightly targeted to this role and company
- Flag any significantly rewritten bullet with [REVIEW]
- **Target <=2 pages total.** Use these bullet counts as a starting budget and
  trim older roles first if the builder fires a page-count warning.

### Output format

Save to: `working/resume_content.json`

```json
{
  "company":  "CompanyName",
  "position": "Role Title",
  "summary": [
    "First summary paragraph.",
    "Second summary paragraph (skills list, voice line, etc.)"
  ],
  "experience": [
    {
      "title":   "Your Most Recent Role",
      "company": "Your Most Recent Employer",
      "dates":   "Jan 2020 – Present",
      "bullets": [
        "Tailored bullet matching JD language.",
        "..."
      ]
    },
    {
      "title":   "Prior Role",
      "company": "Employer",
      "dates":   "Jan 2015 – Dec 2019",
      "bullets": ["..."]
    }
  ],
  "key_project": {
    "title":    "Project Name  —  Subtitle",
    "subtitle": "role  duration  context",
    "bullets":  [
      "What you built and why it mattered.",
      "Technical approach and stack.",
      "Outcome / impact."
    ]
  },
  "education": [
    {"title": "Certification Name  —  Year", "sub": "Issuer  Context"},
    {"title": "Degree or Equivalent", "sub": "Institution"}
  ]
}
```

### Generate PDF

Run the resume builder:
```
python scripts/resume_builder.py working/resume_content.json
```

This clones your master DOCX template, replaces the left column with the JSON
content, and outputs a DOCX + PDF in the company folder under jobhunt_root.

## Step 7 — Cover Letter Writer (if yes)

Using master_resume.json, gap_analysis.json, job_posting.json:

Write cover letter to: `working/cover_letter_draft.txt`

### Rules
- Open with something specific about the company — not generic
- Lead with 1-2 strongest matches for this role
- Address the most significant gap honestly but briefly — don't open with the gap
- Write in the candidate's natural voice
- **Keep it SHORT: 4 tight paragraphs, target ~230 words, hard cap 280.**
- One idea per sentence — no run-ons stacking 5+ accomplishments
- Pick the 2-3 strongest proofs per paragraph; cut the rest
- Flag any generic section with [REWRITE] for review

### File format

```
[Your Name]
[email]  |  [phone]  |  [linkedin]

[Date]

[Company] Hiring Team

Dear [Company] Hiring Team,

[Body paragraphs]

Sincerely,

[Your Name]
```

### Generate PDF

```
python scripts/cover_letter_builder.py "[company_name]"
```

## Step 8 — Reviewer and Rescorer

Re-run gap analysis against resume_content.json and cover_letter_draft.txt.
Compare initial score to final score.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Review Complete
 Initial score:  XX/100
 Final score:    XX/100
 Improvement:   +XX pts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Items flagged for your review:
 [REVIEW] — bullet text
 [REWRITE] — cover letter section
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Step 9 — Save Outputs

Copy the working files to the company folder under jobhunt_root:

```powershell
$co  = "[company_name]"
$dst = Join-Path $env:JOBHUNT_ROOT $co
Copy-Item "working\resume_content.json"    "$dst\resume_content.json"
Copy-Item "working\cover_letter_draft.txt" "$dst\cover_letter_draft.txt" -ErrorAction SilentlyContinue
Copy-Item "working\job_posting.json"       "$dst\job_posting.json"
Copy-Item "working\gap_analysis.json"      "$dst\gap_analysis.json"
```

Final folder contents (if applied with cover letter):
```
<jobhunt_root>\[company]\
├── [YourName]-Resume-Designed.pdf
├── [YourName]-Resume-Designed.docx
├── [YourName]-Cover-Letter.pdf
├── [YourName]-Resume.pdf          (ATS version)
├── resume_content.json
├── cover_letter_draft.txt
├── job_posting.json
└── gap_analysis.json
```

Print when done:
```
[Company] - [Position] complete
  Resume PDF:    [YourName]-Resume-Designed.pdf
  Cover letter:  [YourName]-Cover-Letter.pdf  [or: skipped]
  Output:        <jobhunt_root>\[company]\
```

# Build Master Resume

Scan your existing resume files and build or update `master_resume.json` in this repo.

## Source Files

Scan these locations (set paths in `config.json`):
- All per-company subfolders under `jobhunt_root` — each subfolder name is a company
- Within each company folder: any PDF, DOCX, or TXT file (resume, cover letter, form fill)
- Skip the `hirecraft/` folder itself and any `working/` directories

For every file processed, record it in the `sources` array with:
- `file`: relative path
- `type`: resume | cover_letter | form_fill | work_history | misc
- `company`: company folder name, or "misc" for root-level files
- `processed_at`: timestamp

## Re-Run Behavior

If `master_resume.json` already exists:
- DO NOT wipe it
- Merge new findings into existing entries
- Add new bullets/variants without duplicating ones already present
- Append new sources to the sources array
- Update `last_updated` timestamp

## Schema

Output must match this exact structure:

```json
{
  "last_updated": "",
  "identity": {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "website": ""
  },
  "summary_variants": [
    { "text": "", "source": "", "context": "" }
  ],
  "experience": [
    {
      "employer": "Employer Name",
      "domain": "",
      "bullets": [
        { "text": "", "source": "", "tags": [] }
      ]
    }
  ],
  "skills": {
    "technical": [{ "name": "", "sources": [] }],
    "tools": [{ "name": "", "sources": [] }],
    "soft": [{ "name": "", "sources": [] }]
  },
  "latent_skills": [],
  "certifications": [
    { "name": "", "issuer": "", "year": "", "status": "", "source": "" }
  ],
  "education": [
    { "degree": "", "institution": "", "year": "", "source": "" }
  ],
  "projects": [
    {
      "name": "",
      "employer": "",
      "bullets": [
        { "text": "", "source": "", "tags": [] }
      ]
    }
  ],
  "personal_details": [
    { "text": "", "source": "", "category": "" }
  ],
  "personal_interests": [
    { "name": "", "keywords": [] }
  ],
  "applied_companies": [
    { "company": "", "role": "", "source": "" }
  ],
  "passed_on_companies": [
    { "company": "", "role": "", "source": "" }
  ],
  "honesty_constraints": [],
  "sources": []
}
```

## Tagging Rules

Tag every bullet and skill consistently. A bullet can have multiple tags.

- Integration: `hl7`, `fhir`, `edi`, `x12`, `api`, `interfaces`, `interoperability`
- Platforms: name the actual platform (e.g. `epic`, `cerner`, `workday`)
- Data: `sql`, `etl`, `python`, `powerbi`, `data-mapping`
- Infrastructure: `linux`, `docker`, `azure`, `networking`, `security`
- Domain: use your industry (e.g. `healthcare-it`, `fintech`, `saas`)
- Delivery: `implementation`, `project-management`, `stakeholder`, `training`, `go-live`

## Extraction Rules

### Summaries
Extract every distinct summary or objective statement. Note the company/role context.

### Experience Bullets
- Extract every bullet from every resume version
- Store ALL variants separately — do not merge or deduplicate
- Keep original wording exactly as written
- Tag each bullet

### Skills
Deduplicate by name. When the same skill appears in multiple sources, add all sources to the `sources` array.

### Personal Details
Pull from cover letters: personality statements, motivations, "why this field" framing, values, anything that adds color beyond the resume facts. Categorize as: motivation | personality | achievement | context

### Honesty Constraints
As you process files, flag any claims that appear inconsistently across versions (different metrics for the same achievement, different dates, overclaimed skills). Add these as constraint notes in `honesty_constraints` so the gap analyzer can enforce them.

### Applied vs Passed
- Applied companies come from company subfolders that contain a submitted resume
- Passed companies come from any "passed on" or "did not pursue" tracking file you maintain
- Keep them in separate arrays

## Output

Write the completed JSON to: `master_resume.json` in this repo root.

After writing, print a summary:
- Total files processed
- Total bullets extracted
- Total skills identified
- Any files that could not be read or were skipped, and why
- Any inconsistencies flagged for your review

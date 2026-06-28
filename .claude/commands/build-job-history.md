# Build Job History

Scan your Obsidian company notes and build or update `job_history.json` in this repo.

## Source Locations

Set these paths in your own config or update them here before running:
- Your Obsidian vault: `Company notes folder` (applied jobs)
- Your Obsidian vault: `Did not pursue subfolder` (declined/passed jobs)

Each `.md` file in these folders represents one application.

## Re-Run Behavior

If `job_history.json` already exists:
- DO NOT wipe it
- Match existing entries by company + position combination
- Update fields if new data is present, do not overwrite with blanks
- Append new entries for any files not already represented
- Update `last_updated` timestamp

## Extraction Rules

Each company note uses a consistent frontmatter + section structure. Extract:

### From Frontmatter
- company
- position
- status
- date_found
- date_applied
- source
- salary_range
- reply_received
- interview_scheduled
- offer_received

### From the Assessment Section
- strong_matches: array of bullet strings
- honest_gaps: array of bullet strings
- overall_summary: the paragraph text under Overall/Verdict
- verdict: Applied / Passed / Declined / etc.

### From declined/passed notes
- Set `outcome` to "declined"
- Extract any notes explaining why from the Notes section
- If no reason given, set `decline_reason` to null

### From applied notes
- Set `outcome` based on frontmatter flags:
  - `offer_received: true` → "offer"
  - `interview_scheduled: true` → "interviewed"
  - `reply_received: true` → "replied"
  - all false → "no_response"

## Schema

```json
{
  "last_updated": "",
  "pattern_analysis": {
    "common_gaps": [],
    "common_strengths": [],
    "decline_reasons": [],
    "salary_ranges_seen": []
  },
  "applications": [
    {
      "company": "",
      "position": "",
      "status": "",
      "date_applied": "",
      "date_found": "",
      "source": "",
      "salary_range": "",
      "outcome": "",
      "decline_reason": null,
      "strong_matches": [],
      "honest_gaps": [],
      "overall_summary": "",
      "verdict": "",
      "reply_received": false,
      "interview_scheduled": false,
      "offer_received": false,
      "source_file": ""
    }
  ]
}
```

## Pattern Analysis

After processing all files, populate `pattern_analysis`:

- `common_gaps`: gaps that appear in 2+ honest_gaps sections (a skill showing up repeatedly = a known recurring gap you should address or acknowledge)
- `common_strengths`: matches that appear in 2+ strong_matches sections
- `decline_reasons`: all extracted decline reasons, deduplicated and summarized
- `salary_ranges_seen`: min/max from all postings that included salary data

## Output

Write completed JSON to: `job_history.json` in this repo root.

After writing, print a summary:
- Total files processed (applied vs declined breakdown)
- Outcome distribution (no_response / replied / interviewed / offer / declined)
- Top 3 common gaps found across applications
- Top 3 common strengths found across applications
- Salary range spread across all postings with salary data
- Any files that could not be parsed or were missing expected sections

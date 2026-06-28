# Honesty in AI-Assisted Job Applications

The most common failure mode of AI-assisted job searching is fabrication. The AI does not know
what you have done. It knows what you told it. When you give it a job description and a vague
resume, it fills gaps with plausible-sounding details that may never have happened.

This document explains how HireCraft approaches that problem, and the principles behind it.

---

## The Core Rule

**Every claim in your resume and cover letter must trace to something real.**

If you cannot point to a specific project, role, or experience that supports a claim, the claim
gets cut. Not softened. Not reframed. Cut.

This is not just an ethical position. It is a practical one. Interviewers probe. A bullet you
cannot speak to in depth is a liability, not an asset. A fabricated metric will be fact-checked.
A stretched skill will surface in a technical screen.

---

## The Honesty Constraint System

HireCraft uses a `honesty_constraints` field in `master_resume.json` to make your specific
limits explicit and enforceable. When the AI drafts anything, it checks against these rules.

**Examples of constraints you might add:**

```json
"honesty_constraints": [
  "Tool X is homelab/self-study only. Never imply production use.",
  "Named clients must trace to real experience. Do not invent company names.",
  "Project Y: I supported this, I did not lead it. Never write 'led'.",
  "Metric Z was estimated, not measured. Do not present it as a hard number.",
  "Skill A: 'familiar' level only. Do not claim proficiency."
]
```

Write your own constraints based on your actual experience. The more specific, the more
useful. Add one every time you catch the AI overclaiming something about you.

---

## Handling Skill Gaps Honestly

When a job description requires something you have not done, you have three options:

**Name the gap.** Say directly that you have not done it, then lean on adjacent strength
and fast-ramp credibility. Honest gap acknowledgment paired with confidence often lands
better than a stretch claim that unravels in the interview.

**Lead with what transfers.** You may not have production experience with Tool X, but you
have deep experience with a comparable tool. Make that connection explicit and accurate.

**Flag it in the cover letter.** A brief, confident acknowledgment of a domain gap
with a sentence on how you would close it signals self-awareness. Most hiring managers
appreciate it more than a candidate who pretends the gap does not exist.

What you should never do is imply you have done something you have not. "Familiar with X"
when you mean "heard of X" is a fabrication in slow motion.

---

## Apply Directly From the Company Website

This is one of the highest-leverage habits in a job search and most candidates skip it.

**Why it matters:**

Aggregators (LinkedIn Easy Apply, Indeed, Handshake) route your application through a
third-party layer. That means:
- Your resume may get reformatted or parsed incorrectly before it reaches the ATS
- The posting may be stale. Aggregators cache listings for days or weeks after a role closes.
- "Easy Apply" signals lower intent. Recruiters can see how you applied.
- You lose visibility into where your application actually went and whether it landed

**Applying directly on the company's ATS (Workday, Greenhouse, iCIMS, Lever, Ashby):**
- Your formatted PDF is submitted as-is
- You get a confirmation with a requisition number you can reference later
- You can verify the posting is still live before investing time in the application
- It signals that you found the role deliberately, not through a generic feed

**How to verify a posting is live before applying:**

| Portal | How to check |
|---|---|
| Workday | The public URL returns HTTP 200 even when closed. Hit the CXS JSON API: `https://{tenant}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job/{path}` - live returns JSON with a title; dead returns 404 |
| iCIMS | Returns HTTP 410 Gone when closed. Reliable. |
| Greenhouse / Ashby / Lever | Real-time. An empty board or error redirect means closed. |
| LinkedIn / Indeed / aggregators | Do not trust. Verify on the company's own site. |

**The rule:** Find the role on the aggregator if that is how you discovered it. Then go to the
company's careers page, find the same posting, and apply there. Takes 60 seconds and meaningfully
improves your odds.

---

## The Two-AI Review Pattern

HireCraft uses OpenCode for first-pass drafting and Claude Code for review and finalization.
This is not just a cost optimization. It serves a quality function.

OpenCode drafts fast and broadly. Claude's job on the review pass is specifically to catch:
- Claims that cannot be sourced in `master_resume.json`
- Metrics presented as precise when they were estimated
- Skills implied at a level you have not reached
- Named entities (companies, clients, tools, projects) that do not appear in your master

Nothing goes out until it has passed that second check. The AI that drafts should not be
the same AI that signs off.

---

## What This Looks Like in Practice

A well-calibrated application:
- Leads with your strongest real matches for the specific role
- Names gaps honestly but briefly, without dwelling on them
- Uses "proficient" and "hands-on" accurately, and "familiar" or "exposure" when that is the truth
- Does not repeat a claim in the cover letter that is not supported by the resume
- Has been fact-checked against your master resume before anything is submitted

A poorly calibrated application:
- Uses AI boilerplate that sounds impressive but cannot survive a follow-up question
- Claims expertise in tools you have read about
- Lists skills from the job description regardless of actual experience
- Gets through the screen but falls apart in the technical interview

The goal is not to get the interview. The goal is to get the job. Those require different
calibrations. HireCraft is built for the second one.

# HireCraft Workflow

Three diagrams covering the full system: architecture, pipeline, and AI stack.

---

## 1. System Architecture

How everything connects. Obsidian and the folder structure are the source of truth. Everything else reads from or writes back to them.

```mermaid
graph TB
    subgraph MASTER ["Master Data Layer"]
        OB["Obsidian Vault\n─────────────\nCompany notes\nApplication log\nInterview prep\nAgenda / dashboard"]
        MR["master_resume.json\n─────────────\nAll experience\nSkills + latent skills\nHonesty constraints\nSalary targets"]
        FS["Folder Structure\n─────────────\nPer-company folders\nresume_content.json\ncover_letter_draft.txt\nFinal PDFs"]
    end

    subgraph DISCOVER ["Discovery Layer"]
        MAN["Manual\nLinkedIn / job boards\nDirect company sites"]
        CAR["career-ops plugin\nGreenhouse / Ashby / Lever\nWorkday / iCIMS\nZero-token scanner"]
    end

    subgraph PIPELINE ["HireCraft Pipeline"]
        OC["OpenCode\nFirst-pass AI\nDraft + validate\nLower token cost"]
        CL["Claude Code\nSecond-pass AI\nFact-check + finalize\nHonesty enforcer"]
        HC["HireCraft Scripts\napply.py\nresume_builder.py\ncover_letter_builder.py\nlinkedin_icebreaker.py"]
    end

    subgraph OUTPUT ["Output Layer"]
        PDF["Resume PDFs\nDesigned + ATS-safe"]
        CVR["Cover Letter PDF"]
        ICE["Icebreaker Message"]
        LOG["Obsidian note updated\nApplication log updated"]
    end

    MAN --> OC
    CAR --> OC
    MR --> OC
    OB --> OC
    OC --> CL
    CL --> HC
    HC --> PDF
    HC --> CVR
    HC --> ICE
    CL --> LOG
    LOG --> OB
```

---

## 2. Job Processing Pipeline

The step-by-step flow from job found to application sent and tracked.

```mermaid
flowchart TD
    A([Job Found]) --> B{How discovered?}

    B -->|Manual search| C[Paste JD text\nor URL]
    B -->|career-ops scan| D[Auto-pulled\nfrom portal API]

    C --> E
    D --> E

    E["OpenCode: Parse JD\nExtract requirements,\nskills, salary, location"]

    E --> F["Match against\nmaster_resume.json"]

    F --> G{New skills\nin this JD?}

    G -->|Yes| H["OpenCode prompts:\nHave you done this?\nComfort level 0–4?"]

    H --> I{Response}
    I -->|Level 2-4\nsome experience| J["Add to latent_skills\nin master_resume.json"]
    I -->|Level 0-1\nnever done it| K["Log as known gap\ndon't claim it"]

    J --> L
    K --> L
    G -->|No| L

    L["Calculate\nmatch score"]

    L --> M{Match > 50%?}

    M -->|No, not a fit| N["Log as Passed\nUpdate Obsidian note\nDone"]

    M -->|Yes, worth pursuing| O["OpenCode: Draft\nResume content +\nCover letter"]

    O --> P["Claude: Review pass\nFact-check every claim\nAgainst master_resume.json\nFlag overclaims"]

    P --> Q["HireCraft: Generate PDFs\napply.py: designed resume\nresume_builder_ats.py: ATS export\ncover_letter_builder.py: cover letter"]

    Q --> R["Find recruiter profile\nWebSearch for name + desk\nUser pastes Activity tab"]

    R --> S["linkedin_icebreaker.py\nMatch on industry / location\nskills / interests\nGenerate 2-3 options"]

    S --> T["Send connection request\n< 300 chars\nIncludes Job ID"]

    T --> U([Application Submitted])

    U --> V{Recruiter responds?}

    V -->|Reply received| W["Claude: Update Obsidian\nCompany note, reply section\nSet follow_up_due"]
    V -->|Interview booked| X["Claude: Create\nInterview prep doc\nCompany research brief\nSTAR story bank"]
    V -->|No response\nafter ~1 week| Y["Claude: Draft\nFollow-up message"]

    W --> Z["Update application log\nstatus / date / notes"]
    X --> Z
    Y --> Z

    Z --> OB([Obsidian synced\nLog updated])
```

---

## 3. AI Token Stack

OpenCode handles the expensive first-pass work. Claude catches what needs a second set of eyes. Keeps costs down without sacrificing accuracy.

```mermaid
flowchart LR
    JD["Job Description"] --> OC

    subgraph OC_BOX ["OpenCode: First Pass"]
        OC["Parse JD\nMatch skills\nPrompt for gaps\nDraft resume content\nDraft cover letter\nDraft icebreaker"]
    end

    subgraph CL_BOX ["Claude Code: Second Pass"]
        CL["Fact-check every claim\nagainst master_resume.json\nCatch fabricated details\nEnforce honesty constraints\nFinalize output\nUpdate Obsidian"]
    end

    subgraph OUT_BOX ["Output"]
        R["Designed Resume PDF"]
        A["ATS Resume PDF"]
        C["Cover Letter PDF"]
        I["Icebreaker Message"]
        O["Obsidian note updated"]
    end

    OC -->|Draft package| CL
    CL -->|Approved| R
    CL -->|Approved| A
    CL -->|Approved| C
    CL -->|Approved| I
    CL -->|Always| O

    CL -->|Flagged issue| FLAG["[REVIEW] / [REWRITE]\nreturned to user\nbefore anything is sent"]
```

---

## Why This Stack

| Concern | How it's handled |
|---|---|
| Token cost | OpenCode does the heavy first-pass draft work |
| Accuracy | Claude fact-checks every claim against master_resume.json |
| Honesty | Honesty constraints in master_resume.json are enforced on every Claude pass |
| Nothing fabricated | Named entities must trace to master or get cut |
| Nothing sent without review | [REVIEW] flags stop the pipeline before submission |
| Application tracking | Every state change updates Obsidian in the same turn |

#!/usr/bin/env python3
"""
linkedin_icebreaker.py — Generate personalized LinkedIn icebreaker messages
by finding commonalities between a recruiter's profile and your background.

Usage:
  1. Go to the recruiter's LinkedIn profile
  2. Copy their About + Experience sections
  3. Save to a text file (e.g., recruiter.txt)
  4. Run:
       python linkedin_icebreaker.py recruiter.txt
     Or paste directly:
       python linkedin_icebreaker.py --stdin
       (then paste text, Ctrl+Z then Enter to end)

Output: commonalities found + 2-3 icebreaker message options

SETUP
-----
Copy config.example.json to config.json and fill in your details.
Set years_experience, current_company, and target_roles to customize
the generated messages. The candidate profile is loaded from master_resume.json
(see master_resume.example.json for the expected schema).

CUSTOMIZATION
-------------
Add your own industry-specific companies to KNOWN_COMPANIES below and
locations to KNOWN_LOCATIONS. The defaults are healthcare IT focused.
"""

import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPT_DIR.parent
CONFIG_PATH  = REPO_ROOT / "config.json"
MASTER_PATH  = REPO_ROOT / "master_resume.json"
OUTPUT_DIR   = REPO_ROOT / "working" / "icebreaker_outputs"

# Customize these lists for your industry and geography.
KNOWN_COMPANIES = [
    # Healthcare IT vendors / payers / platforms
    "epic", "cerner", "meditech", "allscripts", "nextgen", "eclinicalworks",
    "mirth", "bridgelink", "intersystems", "redox", "athenahealth",
    "change healthcare", "optum", "unitedhealth", "humana", "anthem",
    "aetna", "cigna", "cardinal health", "mckesson", "baxter",
    "bd", "medtronic", "stryker", "j&j", "johnson & johnson",
    "philips", "ge healthcare", "siemens", "boston scientific",
    "microsoft", "amazon", "google", "oracle", "workday", "salesforce",
    "servicenow", "splunk", "datadog", "new relic", "elastic",
    # Add your own regional health systems / employers here
]

KNOWN_LOCATIONS = [
    "new york", "ny", "boston", "chicago", "dallas", "atlanta",
    "seattle", "san francisco", "los angeles", "denver", "philadelphia",
    "pittsburgh", "cleveland", "columbus", "detroit", "minneapolis",
    "st. louis", "kansas city", "nashville", "charlotte", "raleigh",
    "orlando", "tampa", "miami", "phoenix", "portland",
]


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else REPO_ROOT / "config.example.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_cfg = load_config()
_name           = _cfg.get("name", "Your Full Name")
_location       = _cfg.get("location", "City, ST")
_years          = _cfg.get("years_experience", "X")
_company        = _cfg.get("current_company", "Your Most Recent Employer")
_target_roles   = _cfg.get("target_roles", "Solutions Architect / Integration Engineer")


def load_candidate():
    if not MASTER_PATH.exists():
        print(f"Warning: master_resume.json not found at {MASTER_PATH}")
        print("Create it from master_resume.example.json with your real data.")
        return {
            "name": _name, "location": _location.lower(),
            "headline": "", "summary": "", "experience": [],
            "skills": set(), "certifications": set(), "interests": [],
        }

    with open(MASTER_PATH, encoding="utf-8") as f:
        data = json.load(f)

    profile = {
        "name":         data["identity"]["name"],
        "location":     data["identity"]["location"].lower(),
        "headline":     "",
        "summary":      "",
        "experience":   [],
        "skills":       set(),
        "certifications": set(),
        "interests":    data.get("personal_interests", []),
    }

    for s in data.get("summary_variants", []):
        profile["summary"] += " " + s["text"]

    for exp in data.get("experience", []):
        for b in exp.get("bullets", []):
            profile["experience"].append(b["text"].lower())
            profile["skills"].update(t.lower() for t in b.get("tags", []))

    for p in data.get("projects", []):
        for b in p.get("bullets", []):
            profile["experience"].append(b["text"].lower())
            profile["skills"].update(t.lower() for t in b.get("tags", []))

    for cert in data.get("certifications", []):
        profile["certifications"].add(cert["name"].lower())

    for skill in data.get("skills", {}).get("technical", []):
        profile["skills"].add(skill["name"].lower())

    return profile


def extract_recruiter_info(text):
    text_lower = text.lower()
    info = {
        "companies": set(), "locations": set(),
        "skills": set(), "interests": set(), "raw": text,
    }

    for company in KNOWN_COMPANIES:
        if company in text_lower:
            info["companies"].add(company)

    for loc in KNOWN_LOCATIONS:
        if loc in text_lower:
            info["locations"].add(loc)

    skill_patterns = [
        r"\bhl7\b", r"\bfhir\b", r"\bdicom\b", r"\brest\b", r"\bsoap\b",
        r"\bpython\b", r"\bsql\b", r"\betl\b", r"\bssis\b", r"\bpowerbi\b",
        r"\bdocker\b", r"\bkubernetes\b", r"\baws\b", r"\bazure\b", r"\bgcp\b",
        r"\bapi\b", r"\bxml\b", r"\bjson\b", r"\bcsv\b", r"\bx12\b",
        r"\bmirth\b", r"\bbridgelink\b", r"\bepic\b", r"\bcerner\b",
        r"\blinux\b", r"\bwindows\b", r"\bunix\b", r"\bpowershell\b",
        r"\bbash\b", r"\bgit\b", r"\bci/cd\b", r"\bjira\b", r"\bservicenow\b",
        r"\bpacs\b", r"\bvna\b", r"\bhipaa\b", r"\bgdpr\b", r"\bhitrust\b",
        r"\binteroperability\b", r"\bintegration\b", r"\binterface\b",
        r"\bimplementation\b", r"\barchitecture\b", r"\bsolutions architect\b",
    ]
    for pattern in skill_patterns:
        m = re.search(pattern, text_lower)
        if m:
            info["skills"].add(m.group(0).strip())

    interest_keywords = [
        (r"\bctf\b", "ctf"),
        (r"\bbsides\b", "security conferences"),
        (r"\binfosec\b", "infosec"),
        (r"\bsecurity\b", "security"),
        (r"\bhomelab\b", "homelab"),
        (r"\bself-host(ing|ed)?\b", "self-hosting"),
        (r"\bmentor(ing)?\b", "mentoring"),
        (r"\b(running|fitness|gym|workout)\b", "fitness"),
        (r"\b(guitar|music|piano|drums)\b", "music"),
        (r"\b(hiking|camping|outdoors)\b", "outdoors"),
        (r"\b(gaming|games|board games|tabletop)\b", "gaming"),
        (r"\b(billiards|pool|8-ball|9-ball)\b", "billiards"),
        (r"\b(travel(ing|ling)?|wanderlust|adventure)\b", "traveling"),
        (r"\b(family|kids|children|parent|dad|father|parenting)\b", "family"),
        (r"\b(ski(ing|er)?|snowboard|winter sports)\b", "skiing"),
        (r"\b(cook(ing)?|chef|bbq|barbecue|grill(ing)?|smoker)\b", "cooking"),
        (r"\b(whiskey|whisky|bourbon|scotch|craft beer|brewery)\b", "whiskey"),
        (r"\b(church|worship|sound engineer|soundboard)\b", "church/community"),
        (r"\b(documentation|technical writing|knowledge base)\b", "documentation"),
    ]
    for pattern, label in interest_keywords:
        if re.search(pattern, text_lower):
            info["interests"].add(label)

    return info


def find_commonalities(candidate, recruiter):
    matches = {
        "industry": False, "location": False, "companies": [],
        "skills": [], "certifications": [], "interests": [],
    }

    healthcare_keywords = [
        "healthcare", "health", "hospital", "clinical", "medical",
        "patient", "health it", "healthtech", "integration", "interoperability",
        "ehr", "emr", "epic", "cerner", "hl7", "fhir", "pacs", "vna",
    ]
    recruiter_text_lower = recruiter["raw"].lower()
    for kw in healthcare_keywords:
        if kw in recruiter_text_lower:
            matches["industry"] = True
            break

    candidate_loc = candidate["location"].lower()
    for loc_part in candidate_loc.replace(",", "").split():
        if len(loc_part) > 2 and loc_part in recruiter_text_lower:
            matches["location"] = True
            break

    candidate_exp_text = " ".join(candidate["experience"])
    for company in recruiter["companies"]:
        if company in candidate_exp_text:
            matches["companies"].append(company)

    for skill in recruiter["skills"]:
        for cand_skill in candidate["skills"]:
            if skill in cand_skill or cand_skill in skill:
                matches["skills"].append(skill)
                break

    for cert in candidate["certifications"]:
        cert_words = cert.split()
        for word in cert_words:
            if len(word) > 3 and word in recruiter_text_lower:
                matches["certifications"].append(cert)
                break

    for interest in recruiter["interests"]:
        for ci in candidate["interests"]:
            for kw in ci.get("keywords", []):
                if kw.lower() in interest.lower() or interest.lower() in kw.lower():
                    matches["interests"].append(ci["name"])
                    break

    for ci in candidate["interests"]:
        ci_name = ci["name"]
        if ci_name not in matches["interests"]:
            for kw in ci.get("keywords", []):
                if kw.lower() in recruiter_text_lower:
                    matches["interests"].append(ci_name)
                    break

    matches["skills"]      = list(dict.fromkeys(matches["skills"]))
    matches["interests"]   = list(dict.fromkeys(matches["interests"]))
    matches["companies"]   = list(dict.fromkeys(matches["companies"]))

    return matches


def generate_messages(recruiter_name, candidate, matches):
    options = []

    # Option 1: Industry + Location
    hooks = []
    if matches["industry"]:
        hooks.append("recruiting in healthcare IT")
    if matches["location"]:
        hooks.append(f"a fellow {_location.split(',')[0].strip()} area professional")
    if matches["companies"]:
        shared = matches["companies"][:2]
        hooks.append(f"we share {' and '.join(shared)} in common")

    hook = ""
    if hooks:
        hook = hooks[0]
        hook = hook[0].upper() + hook[1:]
        if len(hooks) > 1:
            hook += " — " + " and ".join(hooks[1:])

    if hook:
        msg = (
            f"Hi {recruiter_name},\n\n"
            f"{hook}. I'm a Healthcare IT engineer with {_years} years at {_company} — "
            f"integration engineering, implementation, and client ownership. "
            f"Currently exploring {_target_roles} opportunities and always looking to "
            f"connect with people in this space.\n\n"
            f"Would love to stay in touch."
        )
        options.append({"label": "Industry / Location (safest fit)", "text": msg})

    # Option 2: Shared interest / skill
    if matches["interests"]:
        interest = matches["interests"][0]
        msg = (
            f"Hi {recruiter_name},\n\n"
            f"Saw you're in healthcare IT and also interested in {interest.lower()} — "
            f"same here. I've been at this for {_years} years at {_company} and "
            f"currently exploring {_target_roles} roles.\n\n"
            f"Would be great to connect."
        )
        options.append({"label": "Shared Interest (more personal)", "text": msg})
    elif matches["skills"]:
        top   = list(matches["skills"])[0]
        label = top.upper() if len(top) < 5 else top.title()
        msg = (
            f"Hi {recruiter_name},\n\n"
            f"I see you work with folks in the {label} integration space — "
            f"that's been my focus for {_years} years at {_company}. "
            f"Currently exploring {_target_roles} opportunities.\n\n"
            f"Would love to connect."
        )
        options.append({"label": "Skills Alignment", "text": msg})

    # Option 3: General networking
    msg = (
        f"Hi {recruiter_name},\n\n"
        f"I've been following your work in healthcare technology recruiting and wanted to "
        f"reach out. I come from {_years} years of Healthcare IT at {_company} — "
        f"implementing clinical systems, building interfaces, leading UAT cycles — and I'm "
        f"currently exploring {_target_roles} roles.\n\n"
        f"Would appreciate being on your radar."
    )
    options.append({"label": "General Networking (lowest bar)", "text": msg})

    return options


def _build_checks(matches):
    return [
        ("Industry (Healthcare IT)", matches["industry"]),
        (f"Location ({_location})", matches["location"]),
        ("Companies shared", bool(matches["companies"])),
        ("Skills shared", bool(matches["skills"])),
        ("Certifications shared", bool(matches["certifications"])),
        ("Interests shared", bool(matches["interests"])),
    ]


def print_results(recruiter_name, matches, options, checks):
    print("=" * 64)
    print("  LINKEDIN ICEBREAKER — Commonality Analysis")
    print("=" * 64)
    print(f"\n  Candidate: {_name}")
    print(f"  Recruiter: {recruiter_name}")
    print(f"  Location:  {_location}")

    print("\n" + "-" * 64)
    print("  COMMONALITIES FOUND")
    print("-" * 64)

    for label, found in checks:
        status = "✓" if found else "—"
        print(f"    [{status}] {label}")

    if matches["companies"]:
        print(f"         Companies: {', '.join(matches['companies'][:4])}")
    if matches["skills"]:
        print(f"         Skills:    {', '.join(matches['skills'][:6])}")
        if len(matches["skills"]) > 6:
            print(f"                    ... and {len(matches['skills']) - 6} more")
    if matches["certifications"]:
        print(f"         Certs:     {', '.join(matches['certifications'][:3])}")
    if matches["interests"]:
        shown = matches["interests"][:5]
        print(f"         Interests: {', '.join(shown)}")

    print(f"\n{'=' * 64}")
    print("  ICEBREAKER MESSAGE OPTIONS")
    print("=" * 64)

    for i, opt in enumerate(options, 1):
        print(f"\n  {'─' * 60}")
        print(f"  Option {i} — {opt['label']}")
        print(f"  {'─' * 60}")
        for line in opt["text"].strip().split("\n"):
            print(f"    {line.strip()}")

    print(f"\n{'=' * 64}")
    print("  TIPS")
    print("=" * 64)
    print("  - Always include a connection request message (don't send blank)")
    print("  - Follow up in 3-5 days if no response")
    print("  - Be kind and don't expect an answer")
    print("  - Aim to build a relationship, not just ask for a job")
    print("=" * 64)


def guess_recruiter_name(text):
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) < 60 and not line.startswith(("About", "Experience", "http", "www", "@")):
            full = line.split("|")[0].split(",")[0].strip()
            return full.split()[0]
    return "there"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    company  = None
    leftover = []
    skip = False
    for i, a in enumerate(sys.argv[1:], 1):
        if skip:
            skip = False; continue
        if a == "--company" and i + 1 < len(sys.argv):
            company = sys.argv[i + 1]; skip = True
        elif a.startswith("--company="):
            company = a.split("=", 1)[1]
        else:
            leftover.append(a)

    if not leftover:
        print("Please provide a profile file path or --stdin")
        return

    if leftover[0] == "--stdin":
        print("Paste recruiter profile text, then Ctrl+Z then Enter (Windows) or Ctrl+D (Mac/Linux):")
        text = sys.stdin.read()
    else:
        path = Path(leftover[0])
        if not path.exists():
            print(f"File not found: {path}"); return
        text = path.read_text(encoding="utf-8-sig")

    jobhunt_root = Path(_cfg.get("jobhunt_root", str(REPO_ROOT.parent)))
    if company:
        company_dir = jobhunt_root / company
        out_dir = company_dir if company_dir.exists() else OUTPUT_DIR
    else:
        out_dir = OUTPUT_DIR

    candidate = load_candidate()
    recruiter = extract_recruiter_info(text)
    matches   = find_commonalities(candidate, recruiter)
    rname     = guess_recruiter_name(text)
    options   = generate_messages(rname, candidate, matches)
    checks    = _build_checks(matches)

    print_results(rname, matches, options, checks)

    out_dir.mkdir(parents=True, exist_ok=True)
    ts = out_dir / f"{rname.lower().replace(' ', '_')}.txt"
    with open(ts, "w", encoding="utf-8") as f:
        f.write("=== RECRUITER PROFILE ===\n\n")
        f.write(text)
        f.write("\n\n=== COMMONALITIES ===\n\n")
        for label, found in checks:
            f.write(f"[{'✓' if found else '—'}] {label}\n")
        f.write("\n=== ICEBREAKER OPTIONS ===\n\n")
        for i, opt in enumerate(options, 1):
            f.write(f"Option {i} — {opt['label']}\n")
            f.write(opt["text"] + "\n\n")

    print(f"\n[Saved to {ts}]")


if __name__ == "__main__":
    main()

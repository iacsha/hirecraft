#!/usr/bin/env python3
"""
wizard.py - HireCraft interactive job search wizard.

Run: python scripts/wizard.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Missing dependencies. Run: pip install rich questionary")
    sys.exit(1)

console = Console()

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config.json"
MASTER_RESUME_PATH = REPO_ROOT / "master_resume.json"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_master_resume() -> dict:
    if not MASTER_RESUME_PATH.exists():
        return {}
    with open(MASTER_RESUME_PATH) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def safe_slug(name: str) -> str:
    """Strip path separators and unsafe chars from any user-supplied name used in file paths."""
    slug = name.lower().replace(" ", "_")
    slug = re.sub(r"[^\w\-]", "", slug)
    return slug or "unknown"


# ── AI integration ────────────────────────────────────────────────────────────

def ai_call(prompt: str, label: str = "Thinking...") -> str:
    """
    Try the Claude CLI first. If unavailable, print the prompt and ask the
    user to paste a response. This keeps the wizard functional with or
    without Claude Code installed.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]{label}[/cyan]"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("", total=None)
        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    console.print(
        Panel(
            prompt,
            title="[yellow]Paste this into your AI assistant[/yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    )
    return questionary.text("Paste the AI response here:").ask() or ""


# ── Multiline paste input ─────────────────────────────────────────────────────

def paste_input(label: str) -> str:
    console.print(f"\n{label}")
    console.print("[dim]Paste text, then type END on its own line and press Enter.[/dim]\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


# ── Liveness check ────────────────────────────────────────────────────────────

def check_posting_liveness(url: str) -> str:
    """Returns 'live', 'dead', or 'unknown'."""
    import urllib.request
    import urllib.error

    if not url.startswith(("http://", "https://")):
        return "unknown"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return "live" if resp.status == 200 else "unknown"
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "dead"
    except Exception:
        pass
    return "unknown"


# ── Header ────────────────────────────────────────────────────────────────────

def header() -> None:
    console.print()
    console.print(Panel(
        "[bold cyan]HireCraft[/bold cyan]  "
        "[dim]AI-powered job application toolkit[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()


# ── Onboarding ────────────────────────────────────────────────────────────────

def onboarding() -> dict:
    console.print(Panel(
        "Looks like this is your first run. Let's get you set up.\n"
        "This creates config.json with your personal details.",
        title="[bold]First-Time Setup[/bold]",
        border_style="cyan",
    ))

    prompts = [
        ("name",            "Your full name",                              "Jane Smith"),
        ("name_slug",       "Filename-safe version of your name",          "jane-smith"),
        ("email",           "Email address",                               "jane@example.com"),
        ("phone",           "Phone number",                                "+1 555-555-5555"),
        ("linkedin_url",    "LinkedIn profile URL",                        "https://linkedin.com/in/janesmith"),
        ("linkedin_display","LinkedIn short display text",                 "linkedin.com/in/janesmith"),
        ("location",        "Location (City, State)",                      "Rochester, NY"),
        ("years_experience","Years of professional experience",            "10"),
        ("current_company", "Current or most recent employer",             "Acme Corp"),
        ("target_roles",    "Target role titles, comma separated",         "Integration Engineer, Solutions Architect"),
    ]

    config = {}
    for key, label, placeholder in prompts:
        value = questionary.text(
            f"{label}:",
            instruction=f"  e.g. {placeholder}",
        ).ask()
        config[key] = value.strip() if value else placeholder

    config["target_roles"] = [r.strip() for r in config["target_roles"].split(",")]

    jobhunt_root = questionary.text(
        "Where is your job hunt folder? (absolute path):",
        instruction=f"  e.g. {Path.home() / 'JobHunt'}",
    ).ask()
    config["jobhunt_root"] = (jobhunt_root or str(Path.home() / "JobHunt")).strip()

    resume_template = questionary.text(
        "Resume template filename (inside jobhunt_root):",
        instruction="  e.g. Resume_Template.docx",
    ).ask()
    config["resume_template"] = (resume_template or "Resume_Template.docx").strip()

    save_config(config)
    console.print("\n[green]config.json saved.[/green]")

    if not MASTER_RESUME_PATH.exists():
        example = REPO_ROOT / "master_resume.example.json"
        if example.exists() and questionary.confirm(
            "Copy master_resume.example.json to master_resume.json to get started?",
            default=True,
        ).ask():
            shutil.copy(example, MASTER_RESUME_PATH)
            console.print(
                "[green]master_resume.json created.[/green] "
                "Open it and fill in your real experience before running the pipeline."
            )

    return config


# ── Process a new job ─────────────────────────────────────────────────────────

def process_job(config: dict, master: dict) -> None:
    console.print(Rule("[bold cyan]Process a New Job Posting[/bold cyan]"))

    company = questionary.text("Company name:").ask()
    if not company:
        return
    company = company.strip()

    position = (questionary.text("Job title:").ask() or "Unknown Role").strip()

    posting_url = questionary.text(
        "Posting URL (Enter to skip):",
        instruction="  We will verify it is live before you invest time in the application.",
    ).ask()

    if posting_url and posting_url.strip():
        posting_url = posting_url.strip()
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Checking posting liveness...[/cyan]"),
            transient=True,
            console=console,
        ) as p:
            p.add_task("", total=None)
            liveness = check_posting_liveness(posting_url)

        status_text = {
            "live":    "[green]Posting is live.[/green]",
            "dead":    "[red]Posting appears closed (404/410). Verify before continuing.[/red]",
            "unknown": "[yellow]Could not verify liveness. Check the URL manually.[/yellow]",
        }[liveness]
        console.print(status_text)

        if liveness == "dead":
            if not questionary.confirm("Continue anyway?", default=False).ask():
                return

    jd_text = paste_input("Paste the full job description below.")
    if not jd_text.strip():
        console.print("[red]No job description provided. Cancelling.[/red]")
        return

    # Build analysis prompt
    name = config.get("name", "Candidate")
    years = config.get("years_experience", "")
    tech_skills = [s["name"] for s in master.get("skills", {}).get("technical", [])[:15]]
    tool_skills = [s["name"] for s in master.get("skills", {}).get("tools", [])[:10]]
    skills_block = ""
    if tech_skills or tool_skills:
        skills_block = f"Technical: {', '.join(tech_skills)}\nTools: {', '.join(tool_skills)}"
    constraints = "\n".join(master.get("honesty_constraints", []))

    analysis_prompt = f"""You are evaluating job fit for {name}, a {years}-year professional.

JOB DESCRIPTION:
{jd_text}

CANDIDATE SKILLS:
{skills_block if skills_block else "See master_resume.json for full skill list."}

HONESTY CONSTRAINTS (never imply more than stated):
{constraints if constraints else "None specified. Default to honest, conservative framing."}

Respond in this exact JSON format with no additional text:
{{
  "match_score": <0-100>,
  "strong_matches": ["match 1", "match 2", "match 3"],
  "honest_gaps": ["gap 1", "gap 2"],
  "verdict": "Strong Apply / Apply / Borderline / Pass",
  "summary": "2-3 sentence honest assessment"
}}"""

    response = ai_call(analysis_prompt, label=f"Analyzing fit for {company} - {position}...")

    analysis = {}
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            analysis = json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    if analysis:
        score = analysis.get("match_score", 0)
        color = "green" if score >= 70 else "yellow" if score >= 50 else "red"

        score_table = Table(show_header=False, box=None, padding=(0, 2))
        score_table.add_row("Match Score", f"[{color}][bold]{score}/100[/bold][/{color}]")
        score_table.add_row("Verdict",     f"[bold]{analysis.get('verdict', '')}[/bold]")
        console.print()
        console.print(score_table)

        matches = "\n".join(f"[green]+ {m}[/green]" for m in analysis.get("strong_matches", []))
        gaps    = "\n".join(f"[red]- {g}[/red]"    for g in analysis.get("honest_gaps", []))

        console.print()
        console.print(Panel(
            matches or "[dim]None identified[/dim]",
            title="[green]Strong Matches[/green]",
            border_style="green",
        ))
        console.print(Panel(
            gaps or "[dim]None identified[/dim]",
            title="[red]Honest Gaps[/red]",
            border_style="red",
        ))
        console.print()
        console.print(f"[italic]{analysis.get('summary', '')}[/italic]")
        console.print()

        # Skill gap comfort rating
        gap_list = analysis.get("honest_gaps", [])
        if gap_list:
            console.print("[bold]Rate your actual comfort with each gap (0-4):[/bold]")
            console.print(
                "[dim]0=Never touched  1=Read about it  2=Lab/coursework  "
                "3=Some production  4=Production confident[/dim]\n"
            )
            gap_ratings: dict[str, int] = {}
            for gap in gap_list:
                rating = questionary.select(
                    f"{gap}:",
                    choices=[
                        "0 - Never touched it",
                        "1 - Read about it",
                        "2 - Lab / coursework",
                        "3 - Some production",
                        "4 - Production confident",
                    ],
                ).ask()
                if rating:
                    gap_ratings[gap] = int(rating[0])

            low_count = sum(1 for r in gap_ratings.values() if r <= 1)
            if low_count:
                console.print(
                    f"\n[yellow]{low_count} gap(s) at 0-1 comfort. "
                    "Be ready to address these honestly in your cover letter.[/yellow]"
                )
    else:
        console.print(Panel(response, title="AI Assessment", border_style="cyan"))

    # Decision
    decision = questionary.select(
        "What would you like to do?",
        choices=[
            "Apply - build resume and cover letter",
            "Pass on this role",
            "Save notes and decide later",
        ],
    ).ask()

    if not decision:
        return

    if decision.startswith("Apply"):
        console.print(f"\n[cyan]Building documents for {company}...[/cyan]")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "apply.py"), company],
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            console.print("[green]Documents built.[/green]")
            if questionary.confirm(
                "Generate a recruiter icebreaker while you are here?",
                default=True,
            ).ask():
                generate_icebreaker(config, company=company, position=position)
        else:
            console.print("[red]Build encountered errors. Check output above.[/red]")

    elif decision.startswith("Pass"):
        console.print("[dim]Noted. No documents built.[/dim]")
    else:
        console.print("[dim]Saved. Come back when you are ready.[/dim]")


# ── Recruiter icebreaker ──────────────────────────────────────────────────────

def generate_icebreaker(config: dict, company: str = "", position: str = "") -> None:
    console.print(Rule("[bold cyan]Recruiter Icebreaker[/bold cyan]"))

    if not company:
        company = (questionary.text("Company name:").ask() or "").strip()
    if not position:
        position = (questionary.text("Role title:").ask() or "").strip()

    recruiter_text = paste_input("Paste the recruiter's LinkedIn profile text below.")
    if not recruiter_text.strip():
        console.print("[red]No recruiter profile provided.[/red]")
        return

    name    = config.get("name", "Candidate")
    years   = config.get("years_experience", "")
    targets = config.get("target_roles", [])
    targets_str = ", ".join(targets) if isinstance(targets, list) else str(targets)

    prompt = f"""Write a LinkedIn connection request for {name}, a {years}-year {targets_str} professional.

RECRUITER PROFILE:
{recruiter_text}

ROLE: {position} at {company}

Rules:
- Under 300 characters (LinkedIn connection note hard limit)
- Reference the specific role and company
- Find one genuine point of connection from the recruiter profile
- No flattery or boilerplate opener
- First person, natural tone
- Do not invent anything

Provide 2 short options, numbered."""

    response = ai_call(prompt, label="Drafting icebreaker options...")
    console.print(Panel(response, title="[cyan]Icebreaker Options[/cyan]", border_style="cyan"))

    out_dir = REPO_ROOT / "working" / "icebreaker_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = safe_slug(company)
    out_file = out_dir / f"{slug}.txt"
    out_file.write_text(
        f"Company: {company}\nRole: {position}\n"
        f"Generated: {datetime.now().isoformat()}\n\n{response}",
        encoding="utf-8",
    )
    console.print(f"[dim]Saved to {out_file.relative_to(REPO_ROOT)}[/dim]")


# ── Application pipeline view ─────────────────────────────────────────────────

def view_pipeline(config: dict) -> None:
    console.print(Rule("[bold cyan]Application Pipeline[/bold cyan]"))

    jobhunt_root = config.get("jobhunt_root", "")
    if not jobhunt_root or not Path(jobhunt_root).exists():
        console.print("[yellow]jobhunt_root not configured or path does not exist.[/yellow]")
        return

    root = Path(jobhunt_root)
    dirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not dirs:
        console.print("[dim]No application folders found.[/dim]")
        return

    table = Table(title=f"Applications ({root.name})", border_style="cyan")
    table.add_column("Company", style="bold", no_wrap=True)
    table.add_column("Files", justify="right")
    table.add_column("Last Updated")

    for d in dirs:
        files = list(d.iterdir())
        mtime = datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d")
        table.add_row(d.name, str(len(files)), mtime)

    console.print(table)
    console.print(f"\n[dim]Total: {len(dirs)} companies tracked[/dim]")


# ── Interview prep prompt ─────────────────────────────────────────────────────

def interview_prep(config: dict) -> None:
    console.print(Rule("[bold cyan]Interview Prep[/bold cyan]"))

    company  = (questionary.text("Company name:").ask() or "").strip()
    position = (questionary.text("Role title:").ask() or "").strip()
    notes    = paste_input("Paste any JD, job notes, or context (or type END to skip).")

    name  = config.get("name", "Candidate")
    years = config.get("years_experience", "")

    prompt = f"""Create a concise interview prep brief for {name} ({years} years experience)
interviewing for {position} at {company}.

CONTEXT:
{notes if notes.strip() else "None provided."}

Include:
1. What {company} does in one sentence (if inferable from context)
2. Three likely interview themes based on the role
3. One STAR story prompt for each theme (just the prompt, not the answer)
4. Three smart questions to ask the interviewers
5. One honest gap acknowledgment script if any gaps are apparent

Keep it tight. This is a prep card, not an essay."""

    response = ai_call(prompt, label=f"Building prep brief for {company}...")
    console.print(Panel(response, title=f"[cyan]Interview Prep: {company}[/cyan]", border_style="cyan"))

    out_dir = REPO_ROOT / "working" / "interview_prep"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = safe_slug(company)
    out_file = out_dir / f"{slug}_prep.txt"
    out_file.write_text(
        f"Company: {company}\nRole: {position}\n"
        f"Generated: {datetime.now().isoformat()}\n\n{response}",
        encoding="utf-8",
    )
    console.print(f"[dim]Saved to {out_file.relative_to(REPO_ROOT)}[/dim]")


# ── Liveness check (standalone) ───────────────────────────────────────────────

def check_liveness_interactive() -> None:
    console.print(Rule("[bold cyan]Posting Liveness Check[/bold cyan]"))

    console.print(
        "[dim]Verify a job posting is still open before investing time in the application.\n"
        "iCIMS returns 410 when closed. Workday URLs stay 200 even when closed; "
        "use the company careers page URL directly.[/dim]\n"
    )

    url = (questionary.text("Posting URL:").ask() or "").strip()
    if not url:
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Checking...[/cyan]"),
        transient=True,
        console=console,
    ) as p:
        p.add_task("", total=None)
        status = check_posting_liveness(url)

    messages = {
        "live":    "[green]Live[/green] - posting returned HTTP 200.",
        "dead":    "[red]Closed[/red] - posting returned 404 or 410.",
        "unknown": "[yellow]Unknown[/yellow] - could not determine. Open the URL manually to confirm.",
    }
    console.print(messages[status])


# ── Settings ──────────────────────────────────────────────────────────────────

def settings(config: dict) -> dict:
    console.print(Rule("[bold cyan]Settings[/bold cyan]"))

    table = Table(show_header=True, border_style="dim", show_lines=False)
    table.add_column("Key", style="bold")
    table.add_column("Value", style="dim")
    for k, v in config.items():
        table.add_row(k, json.dumps(v) if isinstance(v, list) else str(v))
    console.print(table)
    console.print()

    key = (questionary.text("Key to update (Enter to go back):").ask() or "").strip()
    if not key or key not in config:
        if key:
            console.print(f"[yellow]Key '{key}' not found.[/yellow]")
        return config

    new_val = questionary.text(
        f"New value for {key}:",
        default=str(config[key]),
    ).ask()
    if new_val is not None:
        config[key] = new_val
        save_config(config)
        console.print(f"[green]{key} updated.[/green]")

    return config


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    header()

    config, master = load_config(), load_master_resume()

    if not config:
        config = onboarding()
        master = load_master_resume()

    first_name = config.get("name", "").split()[0] if config.get("name") else ""
    if first_name:
        console.print(f"[dim]Welcome back, {first_name}.[/dim]\n")

    if not master or not master.get("experience"):
        console.print(Panel(
            "master_resume.json appears empty or missing experience entries.\n"
            "Fill it in before running the pipeline for accurate gap analysis.",
            title="[yellow]Setup Incomplete[/yellow]",
            border_style="yellow",
        ))
        console.print()

    MENU = [
        "Process a new job posting",
        "Generate recruiter icebreaker",
        "Build interview prep brief",
        "View application pipeline",
        "Check posting liveness",
        "Settings",
        "Exit",
    ]

    while True:
        choice = questionary.select("What would you like to do?", choices=MENU).ask()

        if not choice or choice == "Exit":
            console.print("[dim]Good luck out there.[/dim]")
            break

        console.print()

        if choice == "Process a new job posting":
            process_job(config, master)
        elif choice == "Generate recruiter icebreaker":
            generate_icebreaker(config)
        elif choice == "Build interview prep brief":
            interview_prep(config)
        elif choice == "View application pipeline":
            view_pipeline(config)
        elif choice == "Check posting liveness":
            check_liveness_interactive()
        elif choice == "Settings":
            config = settings(config)

        console.print()


if __name__ == "__main__":
    main()

# Enoch Obikoya - Personal Road Safety Assistant Project

import sys
from typing import List, Dict, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


QUIZ_QUESTIONS = [
    {
        "id": 1,
        "question": "A car in front of you has stopped before a zebra crossing to let a pedestrian cross. Are you allowed to overtake it?",
        "options": [
            "A) Yes, if the other lane is completely clear",
            "B) Yes, provided you sound your horn to warn the pedestrian",
            "C) No, you MUST NOT overtake any vehicle that has stopped at a crossing",
            "D) Yes, but only at speeds under 10 mph"
        ],
        "answer": "C",
        "rule": "Rule 191",
        "explanation": "Under Rule 191, you MUST NOT overtake the moving vehicle nearest the crossing or any vehicle that has stopped to allow pedestrians to cross."
    },
    {
        "id": 2,
        "question": "What does a flashing amber light mean at a Pelican crossing?",
        "options": [
            "A) You must come to a complete stop and wait for a green light",
            "B) You MUST give way to pedestrians on the crossing; if clear, you may proceed",
            "C) Only buses and cyclists may proceed",
            "D) Pedestrians no longer have priority"
        ],
        "answer": "B",
        "rule": "Rule 196",
        "explanation": "Rule 196 states that during flashing amber, you MUST give way to pedestrians on the crossing, but if the crossing is clear, you may proceed."
    },
    {
        "id": 3,
        "question": "Can a cyclist legally ride their bicycle across a Toucan crossing?",
        "options": [
            "A) No, cyclists MUST always dismount and walk across all crossings",
            "B) Yes, Toucan crossings are unsegregated crossings where cyclists may cycle across",
            "C) Only children under 12 may cycle across",
            "D) Only if accompanied by a pedestrian"
        ],
        "answer": "B",
        "rule": "Rule 198",
        "explanation": "Rule 198 specifies that Toucan ('two-can') crossings allow cyclists to ride across alongside pedestrians."
    },
    {
        "id": 4,
        "question": "You want to turn right at a yellow box junction. Oncoming traffic is blocking your turn. Can you enter the box?",
        "options": [
            "A) No, you MUST NEVER enter a box junction under any circumstances",
            "B) Yes, you may wait in the box when turning right if only prevented by oncoming traffic",
            "C) Yes, but only for a maximum of 5 seconds",
            "D) Only after 7:00 pm on weekdays"
        ],
        "answer": "B",
        "rule": "Rule 174",
        "explanation": "Under Rule 174, you may enter a box junction and wait when turning right if only prevented by oncoming traffic or vehicles turning right."
    },
    {
        "id": 5,
        "question": "Under the UK Highway Code, what is the 'Hierarchy of Road Users'?",
        "options": [
            "A) The fastest vehicles have priority on all roads",
            "B) Road users most at risk in a collision have highest priority, and heavier vehicles bear greatest responsibility",
            "C) Emergency vehicles always have priority over everyone else",
            "D) Electric vehicles have priority over petrol cars"
        ],
        "answer": "B",
        "rule": "Rule 204 (Hierarchy H1)",
        "explanation": "Rule 204 places pedestrians and cyclists at the top; drivers of vehicles that can cause greatest harm have the greatest responsibility to protect others."
    },
    {
        "id": 6,
        "question": "When overtaking a cyclist on a road with a 30 mph speed limit, how much minimum space should you leave?",
        "options": [
            "A) At least 0.5 metres",
            "B) At least 1.0 metre",
            "C) At least 1.5 metres (and more at higher speeds)",
            "D) As long as you don't hit them, any distance is fine"
        ],
        "answer": "C",
        "rule": "Rule 163",
        "explanation": "Rule 163 advises leaving at least 1.5 metres when overtaking cyclists up to 30 mph, and even more clearance at higher speeds."
    },
    {
        "id": 7,
        "question": "What is the recommended 'Dutch Reach' technique when opening your car door?",
        "options": [
            "A) Kicking the door open gently with your foot",
            "B) Opening the door with the hand furthest from the door, forcing you to look over your shoulder for cyclists",
            "C) Opening the door only halfway and waiting 10 seconds",
            "D) Sounding your horn before opening the door"
        ],
        "answer": "B",
        "rule": "Rule 239",
        "explanation": "Rule 239 recommends the Dutch Reach: using your far hand naturally turns your upper body so you spot approaching cyclists and pedestrians."
    },
    {
        "id": 8,
        "question": "Can you legally use a handheld mobile phone while stopped at a red traffic light?",
        "options": [
            "A) Yes, because the engine is idling and the vehicle is stationary",
            "B) Yes, as long as it is only to check a text message",
            "C) No, you MUST NOT use a handheld phone while driving, including when stationary in traffic or at red lights",
            "D) Yes, if your hazard warning lights are switched on"
        ],
        "answer": "C",
        "rule": "Rule 149",
        "explanation": "Under Rule 149, you MUST NOT use a handheld phone while driving, which strictly includes being stopped in traffic or at traffic lights."
    }
]


SCENARIOS = [
    {
        "id": 1,
        "title": "Rainy High Street & Pedestrian Crossing",
        "situation": (
            "You are driving down a busy high street at 28 mph in heavy rain. "
            "Ahead, you see a zebra crossing. A mother with a pushchair is waiting at the kerb, "
            "and a cyclist is riding slightly ahead of you on your left side."
        ),
        "question": "What is your correct course of action according to the Highway Code?",
        "choices": [
            "1. Accelerate gently past the cyclist so you clear the crossing before the pedestrian steps out.",
            "2. Slow down well in advance, check mirrors, leave ample space for the cyclist, and prepare to stop to allow the pedestrian to cross.",
            "3. Sound your horn to alert the pedestrian not to step out in wet weather, then continue."
        ],
        "best_choice": "2",
        "rules_applied": ["Rule 195 (Zebra Crossings)", "Rule 126 (Stopping in Rain)", "Rule 212 (Space for Cyclists)"],
        "coaching": (
            "Excellent decision! In wet weather, stopping distances double (Rule 126). "
            "Rule 195 states you SHOULD be ready to slow down or stop for pedestrians waiting to cross, "
            "and Rule 212 requires leaving plenty of room for cyclists, especially on slippery surfaces."
        )
    },
    {
        "id": 2,
        "title": "Emergency Vehicle at a Red Traffic Light",
        "situation": (
            "You are the first car stopped at a red traffic light at a busy junction. "
            "Behind you, an ambulance with blue flashing lights and sirens approaches, unable to squeeze past."
        ),
        "question": "What should you legally do?",
        "choices": [
            "1. Drive through the red light into the junction to clear the path for the ambulance.",
            "2. Stay stopped behind the solid white stop line until the light turns green; do not break the law or endanger others.",
            "3. Mount the pavement immediately, even if pedestrians are walking there."
        ],
        "best_choice": "2",
        "rules_applied": ["Rule 219 (Emergency Vehicles)", "Rule 176 (Traffic Lights)"],
        "coaching": (
            "Correct! Rule 219 emphasizes that while you MUST give way to emergency vehicles, "
            "you MUST NOT break the law (such as running a red light under Rule 176 or mounting pavements) "
            "as doing so could cause a severe collision in the junction."
        )
    }
]


# Enoch Obikoya - Interactive quiz, hazard scenarios, and rule browser presentation
class InteractivePresenter:
    @staticmethod
    def print_banner():
        if RICH_AVAILABLE:
            banner = (
                "[bold yellow]THE ZEBRA CROSSING[/bold yellow] - [bold white]UK Road Safety Assistant[/bold white]\n"
                "[dim]Powered by ChromaDB + BM25 Hybrid Retrieval and Local Qwen2.5-1.5B reasoning[/dim]"
            )
            console.print(Panel(banner, border_style="yellow", padding=(1, 2)))
        else:
            print("=" * 78)
            print("THE ZEBRA CROSSING - UK Road Safety Assistant")
            print("=" * 78)

    @staticmethod
    def print_assistant_response(response: Dict):
        answer = response.get("answer", "")
        legal = response.get("legal_weight", "GUIDELINE")
        retrieved = response.get("retrieved_rules", [])
        elapsed = response.get("elapsed_seconds", 0.0)
        suggestions = response.get("suggestions", [])
        is_conversational = response.get("is_conversational", False)

        if RICH_AVAILABLE:
            if is_conversational:
                badge = "[bold white on green] INTERACTIVE CHAT [/bold white on green]"
            elif legal == "MUST":
                badge = "[bold white on red] MANDATORY LAW (MUST) [/bold white on red]"
            elif legal == "SHOULD":
                badge = "[bold black on yellow] ADVISORY GUIDANCE (SHOULD) [/bold black on yellow]"
            else:
                badge = "[bold white on blue] OUT OF DOMAIN [/bold white on blue]"

            content = f"{badge}\n\n[bold white]{answer}[/bold white]\n\n"
            content += f"[dim]Model: Qwen2.5-1.5B-Instruct • Generated in {elapsed:.2f}s[/dim]"

            panel_title = "[bold green]The Zebra Crossing[/bold green]" if is_conversational else "[bold cyan]Road Safety Assistant[/bold cyan]"
            panel_border = "green" if is_conversational else "cyan"
            console.print(Panel(content, title=panel_title, border_style=panel_border))

            if retrieved and not is_conversational:
                table = Table(title="Relevant Rules Retrieved", show_header=True, header_style="bold magenta")
                table.add_column("Rule ID", style="bold yellow", width=12)
                table.add_column("Title / Header", style="white")
                table.add_column("Status", width=10)
                table.add_column("Distance", justify="right", width=10)

                for r in retrieved:
                    r_legal = r.get("legal_weight", "SHOULD")
                    r_style = "[red]MUST[/red]" if r_legal == "MUST" else "[yellow]SHOULD[/yellow]"
                    table.add_row(
                        r.get("rule_id", "Unknown"),
                        r.get("title", r.get("header", "")),
                        r_style,
                        f"{r.get('distance', 0.0):.3f}"
                    )
                console.print(table)

            if suggestions:
                sugg_text = "\n".join([f"  * {s}" for s in suggestions])
                console.print(Panel(sugg_text, title="[bold green]You might also want to ask:[/bold green]", border_style="green"))
        else:
            print("\n" + "=" * 70)
            label = "INTERACTIVE CHAT" if is_conversational else f"ASSISTANT [{legal}]"
            print(f"{label}:")
            print(answer)
            print(f"(Response generated in {elapsed:.2f}s)")
            print("-" * 70)

            if retrieved and not is_conversational:
                print("RELEVANT RULES RETRIEVED:")
                for r in retrieved:
                    print(f"  * {r.get('header', '')} [{r.get('legal_weight', 'SHOULD')}] (Dist: {r.get('distance', 0.0)})")

            if suggestions:
                print("\nYOU MIGHT ALSO WANT TO ASK:")
                for s in suggestions:
                    print(f"  * {s}")
            print("=" * 70 + "\n")


def run_quiz_session():
    print("\n" + "=" * 78)
    print("THE ZEBRA CROSSING - INTERACTIVE ROAD SAFETY QUIZ")
    print("Test your knowledge of UK traffic rules, crossings, and priority!")
    print("=" * 78 + "\n")

    score = 0
    total = len(QUIZ_QUESTIONS)

    for i, item in enumerate(QUIZ_QUESTIONS, 1):
        print(f"\n[Question {i}/{total}]")
        print(f"{item['question']}\n")
        for opt in item["options"]:
            print(f"   {opt}")

        while True:
            choice = input("\nYour answer (A, B, C, D) or 'q' to quit: ").strip().upper()
            if choice in ("A", "B", "C", "D", "Q"):
                break
            print("Please enter A, B, C, or D.")

        if choice == "Q":
            print("\nQuiz exited early.")
            break

        if choice == item["answer"]:
            score += 1
            print(f"\n[CORRECT] Excellent road knowledge.")
        else:
            print(f"\n[INCORRECT] The correct answer was {item['answer']}.")

        print(f"   Authority: {item['rule']}")
        print(f"   Note: {item['explanation']}\n")
        print("-" * 70)

    print("\n" + "=" * 78)
    percentage = (score / total) * 100
    if percentage >= 80:
        badge = "EXPERT DRIVER & PEDESTRIAN ADVOCATE"
    elif percentage >= 60:
        badge = "SAFE ROAD USER"
    else:
        badge = "TIME FOR A HIGHWAY CODE REFRESHER"

    print(f"QUIZ FINISHED! Your Score: {score}/{total} ({percentage:.0f}%) - {badge}")
    print("=" * 78 + "\n")


def run_scenario_session():
    print("\n" + "=" * 78)
    print("INTERACTIVE ROAD SCENARIOS - 'WHAT WOULD YOU DO?'")
    print("Put yourself in the driver's seat and make the safe call!")
    print("=" * 78 + "\n")

    for sc in SCENARIOS:
        print(f"\n--- {sc['title']} ---")
        print(f"\nSituation:\n{sc['situation']}\n")
        print(f"Question: {sc['question']}\n")
        for c in sc["choices"]:
            print(f"   {c}")

        while True:
            ans = input("\nChoose (1, 2, 3) or 'q' to quit: ").strip()
            if ans in ("1", "2", "3", "q", "Q"):
                break
            print("Please choose option 1, 2, or 3.")

        if ans.lower() == "q":
            print("\nScenario practice exited.")
            break

        if ans == sc["best_choice"]:
            print("\n[TOP CHOICE] Safe, legal, and considerate driving.")
        else:
            print(f"\nCaution: Option {sc['best_choice']} is the safest legal choice.")

        print(f"\nCoaching:\n{sc['coaching']}")
        print(f"Rules Involved: {', '.join(sc['rules_applied'])}\n")
        print("-" * 70)


def browse_rules_catalog(rag):
    print("\n" + "=" * 78)
    print("UK HIGHWAY CODE RULES CATALOG")
    print("=" * 78)
    print("Choose a category to browse:")
    print("  [1] Pedestrian Crossings (Zebra, Pelican, Puffin, Toucan, Pegasus)")
    print("  [2] Junctions, Stop Lines & Signals")
    print("  [3] Roundabouts & Lane Discipline")
    print("  [4] Vulnerable Road Users (Pedestrians, Cyclists, Horses)")
    print("  [5] Speed Limits, Stopping Distances & Overtaking")
    print("  [6] Parking, Waiting & Dutch Reach")
    print("  [7] All Rules")
    print("  [q] Back to main menu")
    print("-" * 78)

    categories = {
        "1": ["zebra", "pelican", "puffin", "toucan", "pegasus", "crossing"],
        "2": ["junction", "stop line", "give way", "box junction", "traffic light"],
        "3": ["roundabout"],
        "4": ["vulnerable", "pedestrian", "cyclist", "horse", "children"],
        "5": ["speed", "stopping", "overtaking"],
        "6": ["parking", "waiting", "dutch reach", "pavement"]
    }

    choice = input("\nEnter category number > ").strip()
    if choice.lower() in ("q", "quit", "exit"):
        return

    all_rules = rag.get_all_rules_summary()

    if choice == "7":
        matched = all_rules
    elif choice in categories:
        keywords = categories[choice]
        matched = [
            r for r in all_rules
            if any(k in r["header"].lower() or k in r["text"].lower() for k in keywords)
        ]
    else:
        print("Invalid choice.")
        return

    print(f"\nShowing {len(matched)} matching rules:")
    print("-" * 78)
    for r in matched:
        weight_tag = f"[{r['legal_weight']}]"
        print(f"• {r['rule_id']}: {r['title']} {weight_tag}")

    detail = input("\nType a Rule ID (e.g. 'RULE 195' or '195') to view full text, or press Enter: ").strip()
    if detail:
        clean_num = detail.replace("RULE", "").strip()
        found = [r for r in all_rules if clean_num in r["rule_id"]]
        if found:
            rule_item = found[0]
            print("\n" + "=" * 70)
            print(f"{rule_item['header']}")
            print("=" * 70)
            print(rule_item["text"])
            print("=" * 70 + "\n")
        else:
            print(f"Rule '{detail}' not found.")

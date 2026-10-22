# Enoch Obikoya - Personal Road Safety Assistant Project
# Main application entry point developed by Enoch Obikoya

import sys
import os
import argparse
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rag import RuleRAG
from models import LocalQwenLLM
from assistant import RoadSafetyAssistant
from interactive import (
    InteractivePresenter,
    run_quiz_session,
    run_scenario_session,
    browse_rules_catalog
)


def ask_assistant(rag: RuleRAG, llm: LocalQwenLLM, question: str, verbose: bool = False):
    retrieved_rules, status_msg = rag.retrieve(
        query=question,
        top_k=3,
        distance_threshold=RuleRAG.DEFAULT_DISTANCE_THRESHOLD
    )

    if not retrieved_rules:
        fallback_ans = (
            "I am not sure based on the traffic rules in my database. "
            "I am designed specifically to answer UK road safety questions."
        )
        if verbose:
            print(f"[Guardrail] {status_msg}")
        return fallback_ans, []

    answer = llm.generate_answer(question, retrieved_rules)
    return answer, retrieved_rules


def interactive_session(assistant: RoadSafetyAssistant):
    InteractivePresenter.print_banner()

    print("Welcome! You can ask any traffic rule, road safety, or Highway Code question.")
    print("Interactive Commands:")
    print("  • Type any question and press Enter")
    print("  • 'quiz'          : Take a quick 8-question road safety quiz")
    print("  • 'scenario'      : Practice real-world driving situations ('What would you do?')")
    print("  • 'browse'        : Browse rules by topic (Crossings, Junctions, Roundabouts, etc.)")
    print("  • 'search <term>' : Search rules by keyword (e.g. 'search cyclist', 'search zebra')")
    print("  • 'rule <number>' : View full text of a specific rule (e.g. 'rule 195')")
    print("  • 'history'       : View questions asked in this session")
    print("  • 'help'          : Show commands and tips")
    print("  • 'web'           : Launch the interactive web browser interface")
    print("  • 'q' or 'exit'   : Quit the assistant")
    print("-" * 78)
    print("Sample questions you can try right now:")
    print("  1. Can I overtake someone stopped at a zebra crossing?")
    print("  2. What should I do when the amber light is flashing at a pelican crossing?")
    print("  3. Can a cyclist ride across a Toucan crossing?")
    print("  4. Who has priority when turning into a road with a waiting pedestrian?")
    print("  5. What is the Dutch Reach when opening car doors?")
    print("=" * 78 + "\n")

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue

            cmd_lower = user_input.lower()

            if cmd_lower in ("q", "quit", "exit"):
                print("\nThank you for using The Zebra Crossing Assistant. Stay safe on the roads!\n")
                break

            if cmd_lower in ("help", "?", "commands"):
                print("\nAvailable Commands:")
                print("  • quiz          : Test your knowledge with interactive quiz")
                print("  • scenario      : Practice driving situations")
                print("  • browse        : Browse Highway Code by category")
                print("  • search <term> : Search rules by keyword (e.g. 'search phone')")
                print("  • rule <num>    : View official rule text (e.g. 'rule 195')")
                print("  • history       : View recent questions")
                print("  • web           : Open the interactive web interface")
                print("  • clear         : Clear the screen")
                print("  • exit or q     : Quit\n")
                continue

            if cmd_lower in ("clear", "cls"):
                os.system("cls" if os.name == "nt" else "clear")
                InteractivePresenter.print_banner()
                continue

            if cmd_lower == "quiz":
                run_quiz_session()
                continue

            if cmd_lower in ("scenario", "practice"):
                run_scenario_session()
                continue

            if cmd_lower in ("browse", "rules", "catalog"):
                browse_rules_catalog(assistant.rag)
                continue

            if cmd_lower.startswith("search "):
                keyword = user_input[7:].strip()
                matches = assistant.rag.search_by_keyword(keyword)
                if matches:
                    print(f"\nFound {len(matches)} rules matching '{keyword}':")
                    for m in matches:
                        print(f"  • {m['rule_id']}: {m['title']} [{m['legal_weight']}]")
                    print()
                else:
                    print(f"\nNo rules found matching '{keyword}'.\n")
                continue

            if cmd_lower.startswith("rule "):
                rule_arg = user_input[5:].strip()
                clean_num = rule_arg.replace("RULE", "").strip()
                all_rules = assistant.rag.get_all_rules_summary()
                matched = [r for r in all_rules if clean_num in r["rule_id"]]
                if matched:
                    r = matched[0]
                    print("\n" + "=" * 70)
                    print(f"{r['header']}")
                    print("=" * 70)
                    print(r["text"])
                    print("=" * 70 + "\n")
                else:
                    print(f"\nRule '{rule_arg}' not found.\n")
                continue

            if cmd_lower == "history":
                if not assistant.history:
                    print("\nNo questions asked yet in this session.\n")
                else:
                    print("\n" + "=" * 60)
                    print("SESSION QUESTION HISTORY:")
                    print("=" * 60)
                    for i, h in enumerate(assistant.history, 1):
                        print(f"{i}. {h['question']} [{h['legal_weight']}]")
                    print("=" * 60 + "\n")
                continue

            if cmd_lower == "web":
                from web_ui import launch_web_ui
                launch_web_ui(assistant)
                continue

            if cmd_lower in ("gui", "streamlit"):
                import subprocess
                print("\nLaunching Streamlit GUI (app.py)...", flush=True)
                print("Open your browser at: http://localhost:8501", flush=True)
                print("Note: The process will keep running to serve the app. Press Ctrl+C in this terminal to stop the server.\n", flush=True)
                subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
                continue

            print("\nSearching Highway Code rules & reasoning...", flush=True)
            response = assistant.ask(user_input)
            InteractivePresenter.print_assistant_response(response)

        except KeyboardInterrupt:
            print("\n\nSession paused. Type 'q' to quit or enter a question to continue.\n")
        except Exception as e:
            print(f"\n[Notice] {e}\n")


# Enoch Obikoya - CLI parsing and component setup
def main():
    parser = argparse.ArgumentParser(description="The Zebra Crossing - Road Safety Assistant")
    parser.add_argument("--quiz", action="store_true", help="Launch interactive Highway Code quiz and exit")
    parser.add_argument("--scenario", action="store_true", help="Launch scenario practice and exit")
    parser.add_argument("--web", action="store_true", help="Launch zero-dependency interactive web interface")
    parser.add_argument("--gui", "--streamlit", action="store_true", dest="streamlit", help="Launch Streamlit GUI")
    parser.add_argument("--port", type=int, default=7860, help="Port for the web UI (default: 7860)")
    parser.add_argument("--question", type=str, default=None, help="Ask a single question and exit")
    args, _ = parser.parse_known_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if getattr(args, "streamlit", False):
        import subprocess
        print("\nLaunching Streamlit GUI (app.py)...", flush=True)
        print("Open your browser at: http://localhost:8501", flush=True)
        print("Note: This terminal will remain running to host the web server.", flush=True)
        print("    Press Ctrl+C at any time to shut down the server.\n", flush=True)
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
        return

    print("=" * 78, flush=True)
    print("THE ZEBRA CROSSING - ROAD SAFETY ASSISTANT", flush=True)
    print("=" * 78, flush=True)
    print("Initializing knowledge base and components...\n", flush=True)

    rag = RuleRAG(data_path="data/rules.txt", persist_dir="./chroma_db")
    llm = LocalQwenLLM(model_id="Qwen/Qwen2.5-1.5B-Instruct")
    assistant = RoadSafetyAssistant(rag=rag, llm=llm)

    if args.quiz:
        run_quiz_session()
        return

    if args.scenario:
        run_scenario_session()
        return

    if args.web:
        from web_ui import launch_web_ui
        launch_web_ui(assistant, port=args.port)
        return

    if args.question:
        resp = assistant.ask(args.question)
        InteractivePresenter.print_assistant_response(resp)
        return

    interactive_session(assistant)


if __name__ == "__main__":
    main()

"""
=============================================================================
THE ZEBRA CROSSING - ROAD SAFETY ASSISTANT (PHASE 1: TEXT-ONLY RAG)
=============================================================================
Static RAG runner designed for Spyder IDE (IPython console / standard Python).
No Gradio, No Docker, No external servers needed.

Features:
1. Vector retrieval using ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
2. Local LLM reasoning using Qwen2.5-1.5B-Instruct
3. Strict guardrail ("I am not sure based on official traffic rules")
4. Interactive Q&A loop in Spyder console
=============================================================================
"""

import sys
import argparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rag import RuleRAG
from models import LocalQwenLLM
from assistant import RoadSafetyAssistant
from main import ask_assistant, interactive_session


def interactive_mode(rag: RuleRAG, llm: LocalQwenLLM):
    """Provides a console loop for testing custom questions inside Spyder."""
    assistant = RoadSafetyAssistant(rag=rag, llm=llm)
    interactive_session(assistant)


def main():
    parser = argparse.ArgumentParser(description="UK Highway Code RAG Assistant")
    parser.add_argument("--no-interactive", action="store_true", help="Skip interactive console prompt")
    args, _ = parser.parse_known_args()

    # Ensure stdout handles UTF-8 on Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 78, flush=True)
    print("THE ZEBRA CROSSING - UK HIGHWAY CODE RAG ASSISTANT (PHASE 1)", flush=True)
    print("=" * 78, flush=True)
    print("Initializing components for Spyder...\n", flush=True)

    rag = RuleRAG(data_path="data/rules.txt", persist_dir="./chroma_db")
    llm = LocalQwenLLM(model_id="Qwen/Qwen2.5-1.5B-Instruct")

    # Interactive Q&A loop in Spyder
    if sys.stdin.isatty() and not args.no_interactive:
        interactive_mode(rag, llm)
    else:
        print("[Info] Initialization completed successfully.", flush=True)


if __name__ == "__main__":
    main()

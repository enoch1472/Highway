"""
assistant.py - Core Road Safety Assistant Engine for The Zebra Crossing.

Encapsulates:
- Query handling through the hybrid RAG + local LLM pipeline.
- Conversational prompt handling loaded from data/interactive_prompts.csv,
  so greetings, farewells, and casual chat get friendly responses instead
  of the out-of-domain refusal.
- Smart context-aware follow-up suggestions (e.g. suggesting related rules).
- Clear legal status extraction (Mandatory Law vs Advisory Guidance).
- Conversation history tracking.
"""

import csv
import os
import time
import re
from typing import List, Dict, Tuple, Optional
from rag import RuleRAG
from models import LocalQwenLLM, extract_rule_numbers, extract_primary_rule_number


# ---------------------------------------------------------------------------
# Conversational Prompt Matcher  (loaded from data/interactive_prompts.csv)
# ---------------------------------------------------------------------------

def _load_interactive_prompts(csv_path: str = None) -> List[Dict]:
    """
    Loads the interactive_prompts.csv file and returns a list of prompt entries.
    Each entry has: category, compiled_patterns (list of regex), response,
    suggestions (list of str), and badge.
    """
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "data", "interactive_prompts.csv")
    prompts: List[Dict] = []
    if not os.path.exists(csv_path):
        return prompts

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            patterns_raw = row.get("patterns", "")
            compiled = []
            for p in patterns_raw.split("|"):
                p = p.strip()
                if p:
                    try:
                        compiled.append(re.compile(
                            r"(?:^|[\s,;!?.])" + re.escape(p) + r"(?:[\s,;!?.]|$)",
                            re.IGNORECASE
                        ))
                    except re.error:
                        pass

            suggestions = [s.strip() for s in row.get("suggestions", "").split("|") if s.strip()]

            prompts.append({
                "category": row.get("category", ""),
                "compiled_patterns": compiled,
                "response": row.get("response", "").strip(),
                "suggestions": suggestions,
                "badge": row.get("badge", "INTERACTIVE CHAT").strip()
            })
    return prompts


# Module-level cache so the CSV is loaded once at import time
_INTERACTIVE_PROMPTS: List[Dict] = _load_interactive_prompts()


def match_interactive_prompt(user_input: str) -> Optional[Dict]:
    """
    Checks whether *user_input* matches any conversational pattern from
    interactive_prompts.csv.  Returns the matching entry dict or None.

    Matching logic:
      - Short inputs (<=6 words) are checked for an exact pattern match
        anywhere in the text.
      - Longer inputs are skipped (they are likely real questions that should
        go to the RAG pipeline).
    """
    cleaned = user_input.strip()
    if len(cleaned.split()) > 6:
        return None

    for entry in _INTERACTIVE_PROMPTS:
        for pat in entry["compiled_patterns"]:
            if pat.search(cleaned):
                return entry
    return None


# Curated dictionary of related questions for interactive follow-up suggestions
TOPIC_SUGGESTIONS: Dict[str, List[str]] = {
    "zebra": [
        "A pedestrian is waiting at the kerb of a zebra crossing. Do I have to stop?",
        "Can I overtake a car stopped at a zebra crossing?",
        "What do the zig-zag white lines next to a zebra crossing mean?"
    ],
    "pelican": [
        "What does the flashing amber light mean at a pelican crossing?",
        "What is the difference between a Pelican and a Puffin crossing?",
        "Can cyclists ride across a Pelican crossing?"
    ],
    "puffin": [
        "How do Puffin crossing sensors know when pedestrians have crossed?",
        "Is there a flashing amber light at a Puffin crossing?",
        "Where are the pedestrian signal indicators located on a Puffin crossing?"
    ],
    "toucan": [
        "Can a cyclist ride across a Toucan crossing without dismounting?",
        "Who shares Toucan crossings?",
        "What is the difference between a Toucan crossing and a Pegasus crossing?"
    ],
    "pegasus": [
        "Who is allowed to use a Pegasus crossing?",
        "How do horse riders operate signals at a Pegasus crossing?",
        "How should drivers pass horses on the road?"
    ],
    "junction": [
        "Who has priority when turning into a road with a waiting pedestrian?",
        "Do I have to come to a complete stop at a Give Way line?",
        "Can I enter a yellow box junction if turning right?"
    ],
    "roundabout": [
        "Who has priority when entering a roundabout?",
        "Which lane should I use when taking the intermediate or straight exit?",
        "Do mini-roundabouts follow the same rules as normal roundabouts?"
    ],
    "cyclist": [
        "How much space must drivers leave when overtaking a cyclist?",
        "Why do cyclists sometimes ride in the middle of the road?",
        "Can cyclists use Advanced Stop Lines at traffic lights?"
    ],
    "phone": [
        "Can I check my mobile phone while stopped at a red traffic light?",
        "Are hands-free mobile phones legal to use while driving?",
        "What is the penalty for using a handheld phone while driving?"
    ],
    "speed": [
        "What is the national speed limit on single carriageway roads?",
        "How does wet weather affect stopping distances?",
        "What is the two-second rule for following distance?"
    ],
    "parking": [
        "What is the Dutch Reach technique for opening car doors?",
        "Can you park on the pavement outside of London?",
        "How close to a junction can you legally park?"
    ]
}

DEFAULT_SUGGESTIONS: List[str] = [
    "Can I overtake someone stopped at a zebra crossing?",
    "Who has priority when turning into a side road with waiting pedestrians?",
    "Can a cyclist ride across a Toucan crossing?"
]


class RoadSafetyAssistant:
    """
    High-level coordinator combining knowledge retrieval,
    local LLM reasoning, follow-up suggestions, and session history.
    """
    def __init__(self, rag: Optional[RuleRAG] = None, llm: Optional[LocalQwenLLM] = None):
        self.rag = rag or RuleRAG()
        self.llm = llm or LocalQwenLLM()
        self.history: List[Dict] = []

    def ask(self, question: str) -> Dict:
        """
        Processes a user question through the RAG + LLM pipeline.
        Before hitting RAG, checks if the input matches a conversational
        prompt from data/interactive_prompts.csv (greetings, thanks, etc.)
        so users get a friendly response instead of the out-of-domain refusal.

        Returns a rich response dictionary containing:
        - answer
        - retrieved_rules
        - legal_weight ('MUST', 'SHOULD', 'OUT_OF_DOMAIN', or 'CONVERSATION')
        - suggestions (2-3 relevant follow-up questions)
        - elapsed_seconds
        """
        clean_q = question.strip()
        t0 = time.time()

        # --- Conversational prompt check (CSV-driven) ---
        chat_match = match_interactive_prompt(clean_q)
        if chat_match:
            elapsed = time.time() - t0
            response_payload = {
                "question": clean_q,
                "answer": chat_match["response"],
                "retrieved_rules": [],
                "primary_rule": None,
                "legal_weight": "CONVERSATION",
                "suggestions": chat_match["suggestions"][:3] or DEFAULT_SUGGESTIONS[:3],
                "elapsed_seconds": round(elapsed, 4),
                "is_fallback": False,
                "is_conversational": True,
                "status_message": f"Matched interactive prompt: {chat_match['category']}"
            }
            self.history.append(response_payload)
            return response_payload

        # --- Standard RAG + LLM pipeline ---
        retrieved_rules, status_msg = self.rag.retrieve(
            query=clean_q,
            top_k=3,
            distance_threshold=RuleRAG.DEFAULT_DISTANCE_THRESHOLD
        )

        elapsed = time.time() - t0

        if not retrieved_rules:
            out_of_scope_ans = (
                "I am not sure based on the traffic rules in my database. "
                "I am designed specifically to answer UK road safety and Highway Code questions."
            )
            response_payload = {
                "question": clean_q,
                "answer": out_of_scope_ans,
                "retrieved_rules": [],
                "primary_rule": None,
                "legal_weight": "OUT_OF_DOMAIN",
                "suggestions": DEFAULT_SUGGESTIONS[:3],
                "elapsed_seconds": round(elapsed, 2),
                "is_fallback": True,
                "status_message": status_msg
            }
            self.history.append(response_payload)
            return response_payload

        # Generate LLM response grounded in retrieved rules
        t_gen0 = time.time()
        answer = self.llm.generate_answer(clean_q, retrieved_rules)
        total_elapsed = time.time() - t0

        # Determine primary rule and legal weight
        top_rule = retrieved_rules[0]
        primary_weight = top_rule.get("legal_weight", "SHOULD")
        if any(r.get("legal_weight") == "MUST" for r in retrieved_rules):
            if "must" in answer.lower():
                primary_weight = "MUST"

        # Generate contextual follow-up questions
        suggestions = self._find_follow_ups(clean_q, retrieved_rules)

        response_payload = {
            "question": clean_q,
            "answer": answer,
            "retrieved_rules": retrieved_rules,
            "primary_rule": top_rule.get("rule_id", ""),
            "legal_weight": primary_weight,
            "suggestions": suggestions,
            "elapsed_seconds": round(total_elapsed, 2),
            "is_fallback": False,
            "status_message": "Success"
        }

        self.history.append(response_payload)
        return response_payload

    def _find_follow_ups(self, question: str, retrieved: List[Dict]) -> List[str]:
        """Identifies 2 to 3 intelligent follow-up suggestions based on query and retrieved rules."""
        text_corpus = (question + " " + " ".join(r.get("header", "") for r in retrieved)).lower()

        found_suggestions: List[str] = []
        for keyword, questions in TOPIC_SUGGESTIONS.items():
            if keyword in text_corpus:
                for q in questions:
                    if q.lower() != question.lower() and q not in found_suggestions:
                        found_suggestions.append(q)
            if len(found_suggestions) >= 3:
                break

        if len(found_suggestions) < 3:
            for q in DEFAULT_SUGGESTIONS:
                if q.lower() != question.lower() and q not in found_suggestions:
                    found_suggestions.append(q)
                if len(found_suggestions) >= 3:
                    break

        return found_suggestions[:3]

    def clear_history(self):
        """Resets conversational history."""
        self.history.clear()

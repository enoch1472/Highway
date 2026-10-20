"""
models.py - Local LLM Reasoning for The Zebra Crossing Assistant.

Features:
- Offline reasoning powered by Qwen2.5-1.5B-Instruct.
- Strict legal authority grounding: preserves mandatory requirements (MUST / MUST NOT)
  versus advisory guidance (SHOULD / SHOULD NOT).
- Hallucination guardrail: verifies cited rule numbers against retrieved context.
  If an uncited or hallucinated rule number is detected, automatically falls back
  to direct official quotes.
"""

import os
import sys
import re
from typing import List, Dict, Optional, Set

# Ensure UTF-8 stdout for Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def extract_rule_numbers(text: str) -> List[str]:
    """Extracts all rule numbers (e.g. '195', '191') mentioned in text."""
    return re.findall(r"\brule\s*(\d+)\b", text, re.IGNORECASE)


def extract_primary_rule_number(rule_id: str) -> Optional[str]:
    """Extracts the numeric identifier from a rule string like 'RULE 195'."""
    match = re.search(r"\b(\d+)\b", rule_id)
    return match.group(1) if match else None


class LocalQwenLLM:
    """
    Encapsulates Qwen2.5-1.5B-Instruct for authoritative, citation-grounded answers.
    Optimized to run on either CUDA GPU or multi-threaded CPU.
    """
    def __init__(self, model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        self.model_id = model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[LLM] Initializing local model {model_id} on {self.device.upper()}...", flush=True)

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=True
        )

        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=dtype,
            device_map="auto" if self.device == "cuda" else None,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )

        if self.device == "cpu":
            self.model.to("cpu")
            torch.set_num_threads(os.cpu_count() or 4)

        self.model.eval()
        print("[LLM] Local LLM loaded successfully and ready for Q&A.", flush=True)

    def _format_fallback_answer(self, top_rule: Dict) -> str:
        """
        Creates a faithful direct quotation from the top-ranked rule
        when hallucination detection catches an ungrounded citation.
        """
        header = top_rule.get("header", "UK Highway Code")
        text = top_rule.get("text", "")
        rule_num = extract_primary_rule_number(top_rule.get("rule_id", ""))
        rule_ref = f"Rule {rule_num}" if rule_num else header

        # Pick the first substantive sentence of the rule
        content_lines = [
            line.strip() for line in text.splitlines()
            if line.strip() and not line.startswith("[RULE") and not line.startswith("#")
        ]
        first_sentence = content_lines[0] if content_lines else text
        return f"According to {rule_ref}, {first_sentence}"

    def generate_answer(
        self,
        question: str,
        retrieved_rules: List[Dict]
    ) -> str:
        """
        Generates an authoritative, cited answer grounded strictly in retrieved rules.

        Enforces:
        - Direct citation of rule number (e.g. 'According to Rule 195, ...').
        - Preserves MUST (mandatory legal requirement) vs SHOULD (advisory).
        - Grounded verification: rejects hallucinations and falls back to rule quote.
        """
        if not retrieved_rules:
            return (
                "I am not sure based on the traffic rules in my database. "
                "I am designed specifically to answer UK road safety questions."
            )

        # Collect valid rule numbers from retrieved context for verification
        valid_rule_nums: Set[str] = set()
        context_blocks: List[str] = []

        for r in retrieved_rules:
            num = extract_primary_rule_number(r.get("rule_id", ""))
            if num:
                valid_rule_nums.add(num)

            is_must = r.get("legal_weight") == "MUST"
            legal_label = "Mandatory Legal Requirement" if is_must else "Advisory Guidance"
            context_blocks.append(f"{r['header']} [{legal_label}]:\n{r['text']}")

        context_str = "\n\n".join(context_blocks)

        system_prompt = (
            "You are a helpful, authoritative UK road safety assistant.\n"
            "Rules you MUST follow:\n"
            "1. Answer using ONLY the provided official rule context.\n"
            "2. Start by directly citing the rule NUMBER, e.g. 'According to Rule 195, ...' or 'Under Rule 171, ...'. Do NOT begin with a bare 'Yes' or 'No'.\n"
            "3. PRESERVE LEGAL AUTHORITY: If a rule says MUST, describe it as a mandatory requirement. If a rule says SHOULD, describe it as advisory/good practice.\n"
            "4. When a question asks what a driver must or should do (e.g. stopping, overtaking, priority), cite the driver regulation rule (e.g. Rule 195, Rule 191) rather than pedestrian advice.\n"
            "5. Clearly restate what the official rule requires or advises drivers and road users to do.\n"
            "6. If the context does not answer the question, state: 'I am not sure based on the traffic rules in my database.'\n"
            "7. Always include the specific rule NUMBER in your answer.\n\n"
            "Example 1 (MUST requirement):\n"
            "Context: [RULE 191] [MUST] Zebra Crossings\nYou MUST NOT park on a crossing or zig-zag markings. You MUST NOT overtake the moving vehicle nearest the crossing.\n"
            "Question: Can I overtake someone stopped at a zebra crossing?\n"
            "Answer: According to Rule 191, drivers MUST NOT overtake the moving vehicle nearest the crossing or any vehicle that has stopped to allow pedestrians to cross.\n\n"
            "Example 2 (SHOULD vs MUST distinction):\n"
            "Context: [RULE 195] [MUST] Zebra Crossings\nYou MUST give way when a pedestrian has moved onto a crossing. You SHOULD give way to pedestrians waiting to cross, and be ready to slow down or stop.\n"
            "Question: Do I have to stop for someone waiting at a zebra crossing?\n"
            "Answer: According to Rule 195, drivers SHOULD give way to pedestrians waiting to cross at the kerb and be ready to slow down or stop, and drivers MUST give way once a pedestrian has stepped onto the crossing.\n\n"
            "Example 3 (Cyclist crossing rule):\n"
            "Context: [RULE 198] [MUST] Toucan Crossings\nToucan crossings are light-controlled crossings which allow cyclists to ride across alongside pedestrians. Cyclists are permitted to cycle across.\n"
            "Question: Can a cyclist ride across this crossing?\n"
            "Answer: According to Rule 198, toucan crossings allow cyclists to ride across alongside pedestrians. Cyclists are permitted to cycle across the crossing."
        )

        user_content = (
            f"Official Rules Context:\n{context_str}\n\n"
            f"Question: {question}\n\n"
            f"Authoritative Answer (cite the rule NUMBER):"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        prompt_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer([prompt_text], return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
            generated_ids = [out[len(inp):] for inp, out in zip(inputs.input_ids, outputs)]
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        # Post-generation Verification & Cleanup
        # 1. Clean accidental leading Yes/No for authoritative tone
        cleaned = re.sub(r"^(?:yes|no)[,\.\s]+", "", response, flags=re.IGNORECASE).strip()
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]

        # 2. Strict citation verification: reject hallucinated rule numbers
        cited_nums = extract_rule_numbers(cleaned)
        hallucinated = [num for num in cited_nums if num not in valid_rule_nums]

        if hallucinated:
            print(f"[Citation Guard] Rejected hallucinated rule citation(s) {hallucinated}. Using official quote.")
            return self._format_fallback_answer(retrieved_rules[0])

        # 3. If no rule number was explicitly cited, prepend top rule citation
        if not cited_nums and cleaned:
            top_rule = retrieved_rules[0]
            top_num = extract_primary_rule_number(top_rule.get("rule_id", ""))
            if top_num:
                cleaned = f"According to Rule {top_num}, {cleaned[0].lower()}{cleaned[1:]}"

        return cleaned if cleaned else self._format_fallback_answer(retrieved_rules[0])

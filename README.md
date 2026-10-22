# The Zebra Crossing - Road Safety Assistant

Developer: Enoch Obikoya
Project: Personal Road Safety Assistant Project

---

**About My Project**

My name is Enoch Obikoya, and this is my personal project. I developed The Zebra Crossing to provide a reliable, offline-first road safety assistant for the UK Highway Code. My goal was to create a system that runs entirely on local consumer hardware without sending personal data to external APIs, while strictly preventing artificial hallucinations.

I designed the assistant around a curated knowledge base of 15 essential UK Highway Code rules covering pedestrian crossings, junction priority, national speed limits, parking safety, and vulnerable road users. A key legal principle I embedded into my project is the distinction between mandatory rules (MUST / MUST NOT), which are legally binding statutory offences under the Road Traffic Act, and advisory guidance (SHOULD / SHOULD NOT).

---

**System Architecture**

Here is the system architecture I designed for my project and how data moves through my pipeline:

```
                       +-----------------------------+
                       | User Query (CLI / Web / UI) |
                       +-----------------------------+
                                      |
                                      v
                        +----------------------------+
                        | Fast Greeting Matcher      |
                        | (checks hello, thanks, etc)|
                        +----------------------------+
                               /              \
                     [Matched]                  [Question]
                         |                          |
                         v                          v
                  Instant Response        +--------------------+
                                          | Hybrid Search Engine|
                                          | - ChromaDB MiniLM  |
                                          | - Lexical BM25     |
                                          +--------------------+
                                                    |
                                                    v
                                       +-------------------------+
                                       | Distance Check (> 0.52) |
                                       +-------------------------+
                                        /                       \
                             [Irrelevant]                       [Relevant Rule]
                                  |                                    |
                                  v                                    v
                         Out-of-Scope Fallback               +--------------------+
                                                             | Local Qwen 2.5 LLM |
                                                             +--------------------+
                                                                       |
                                                                       v
                                                             +--------------------+
                                                             | Citation & MUST /  |
                                                             | SHOULD Legal Check |
                                                             +--------------------+
                                                                       |
                                                                       v
                                                                 Final Answer
```

How I built each stage of my architecture:

* Multiple User Interfaces: I wrote three ways to interact with my assistant depending on the environment: a command-line terminal interface (main.py), a zero-dependency lightweight web server on port 7860 (web_ui.py), and a full dark-mode Streamlit dashboard (app.py). All three call the exact same coordinator in assistant.py.

* Fast Conversational Router: Before running heavy embedding calculations, I pass the input through a compiled regex matcher loaded from my interactive prompts dataset. If someone says hello, asks how the bot works, or says thank you, my system replies in under 5ms without touching the neural models.

* Hybrid Search (Vectors + Keywords): Relying on vector embeddings alone can sometimes miss exact rule numbers, while keyword search alone fails on natural phrasing. In rag.py, I combined both:
  - ChromaDB Vector Store: Encodes questions with sentence-transformers/all-MiniLM-L6-v2 into 384-dimensional embeddings to capture general meaning.
  - Custom BM25 Scorer: Matches exact terminology like "Dutch Reach", "Rule 195", or "pelican crossing".
  - Reciprocal Rank Fusion: Merges vector distances and BM25 scores so the top rules are genuinely relevant.

* 0.52 Distance Guardrail: If someone asks something that has nothing to do with UK driving (like cooking recipes or sports trivia), the semantic distance increases. If the top match is above my 0.52 cutoff, my assistant halts immediately and returns a polite message stating that it only answers UK road safety questions.

* Local Qwen 2.5 Model: When valid rules are retrieved, I send the context and the question to a local Qwen2.5-1.5B-Instruct language model running via HuggingFace Transformers. I instruct the model to reason strictly from the retrieved text so it does not make up facts.

* Citation Verification and Legal Tagging: In models.py, my code inspects the answer to verify that any cited rule number exists in my 15-rule database. It also checks whether the rule is mandatory criminal law (MUST / MUST NOT) or advisory guidance (SHOULD) and displays the appropriate legal badge.

---

**Features I Built**

* Grounded Answers: Every response is directly cited against the 15 official Highway Code rules in my database.
* Legal Distinctions: Clearly marks whether an action is required by law (MUST) or advised as safe practice (SHOULD).
* Out-of-Domain Rejection: Safely declines to answer irrelevant queries outside UK road safety.
* Interactive 8-Question Quiz: An interactive Highway Code quiz with instant feedback, scoring, and performance badges.
* Hazard Perception Scenarios: Real-world driving situations requiring the user to choose the safest defensive driving decision.
* Rule Catalog & Keyword Search: Browse rules by topic or search directly by rule number and keywords.
* Session History: Tracks all questions and responses within a session with clear history support.

---

**Application Screenshots**

Here are screenshots of my assistant running locally across its three primary interface views:

* Road Safety Chat Interface:
![Road Safety Chat Interface](screenshots/chat_interface.png)

* Interactive Road Safety Quiz:
![Interactive Road Safety Quiz](screenshots/quiz_interface.png)

* Highway Code Rules Catalog:
![Official Rules Catalog](screenshots/rules_catalog.png)

---

**Getting Started**

1. Install requirements:

pip install -r requirements.txt

2. Run my interactive terminal assistant:

python main.py

---

**Console Commands**

When running my interactive terminal assistant, you can type your question directly or use any of these commands:

* quiz : Start the 8-question Highway Code quiz.
* scenario : Practice real-world road safety scenarios.
* browse : Browse my loaded Highway Code rules by category.
* search <term> : Search the rules database for a specific keyword.
* rule <number> : Look up a specific rule (e.g. rule 195).
* history : View the questions asked during your session.
* web : Start the local web UI in your browser.
* help : Display available commands.
* exit or q : Quit the program.

---

**Command Line Options**

* python main.py : Starts the standard interactive terminal session.
* python main.py --quiz : Starts the quiz directly.
* python main.py --scenario : Starts the scenario practice directly.
* python main.py --web : Launches my zero-dependency browser interface at http://127.0.0.1:7860.
* python main.py --gui : Launches my Streamlit dashboard at http://localhost:8501.
* python main.py --question "Is it permitted to overtake a car waiting at a zebra crossing?" : Answers a single query and exits.

---

**Project Files**

* app.py : Streamlit dashboard interface.
* assistant.py : Core coordinator managing retrieval, prompt matches, and legal weighting.
* data/rules.txt : My curated dataset of 15 UK Highway Code rules.
* data/interactive_prompts.csv : Conversational triggers for greetings, farewells, and help.
* interactive.py : Terminal CLI presenter, quiz engine, and hazard perception scenarios.
* main.py : Application entry point and command-line argument parser.
* main_phase1.py : Standalone runner for testing in standard Python environments.
* models.py : Local model loader for Qwen2.5-1.5B with rule citation checks.
* rag.py : Knowledge retrieval pipeline combining ChromaDB MiniLM embeddings with BM25.
* web_ui.py : Lightweight web server using Python's built-in http.server.

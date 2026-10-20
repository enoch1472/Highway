# The Zebra Crossing - Road Safety Assistant

A personal project for answering UK Highway Code and road safety questions locally and offline. It uses a hybrid retrieval pipeline (MiniLM embeddings with ChromaDB and BM25 keyword search) paired with a local Qwen2.5-1.5B language model.

---

**Overview**

The project is designed to give grounded answers to UK road rules based on a curated set of 15 key Highway Code rules covering crossings, junctions, speed limits, vulnerable road users, and parking safety.

It distinguishes between mandatory rules (MUST / MUST NOT), where non-compliance is a criminal offense under UK traffic law, and advisory guidance (SHOULD / SHOULD NOT). If a question is outside the scope of the included traffic rules, the assistant safely acknowledges that it does not know rather than guessing.

---

**Features**

* Grounded Answers: Answers reference the specific Highway Code rule numbers in the dataset.
* Mandatory vs Advisory: Clearly marks whether an action is required by law (MUST) or advised as safe practice (SHOULD).
* Interactive Console Mode: Ask questions directly in the terminal, run a short knowledge quiz, or walk through scenario questions.
* Web Interfaces: Includes a lightweight built-in web UI (python main.py --web) and a Streamlit dashboard (streamlit run app.py).
* Curated Rules: Grounded in 15 core UK Highway Code rules.

---

**Getting Started**

1. Install requirements:

pip install -r requirements.txt

2. Run the interactive terminal assistant:

python main.py

---

**Console Commands**

When running the interactive terminal assistant, you can type your question directly or use any of these commands:

* quiz : Start the multiple-choice Highway Code quiz.
* scenario : Practice real-world road safety scenarios.
* browse : Browse the loaded Highway Code rules by category.
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
* python main.py --web : Launches the zero-dependency browser interface at http://127.0.0.1:7860.
* python main.py --gui : Launches the Streamlit dashboard at http://localhost:8501.
* python main.py --question "Can I overtake someone stopped at a zebra crossing?" : Answers a single question and exits.

---

**Project Files**

* app.py : Streamlit dark-mode web application.
* assistant.py : Handles question answering, prompt matches, and follow-up suggestions.
* data/rules.txt : The 15 curated UK Highway Code rules.
* data/interactive_prompts.csv : Conversational triggers for greetings and common queries.
* interactive.py : Terminal interface, quiz questions, and hazard scenarios.
* main.py : Main entry point for the console assistant and launcher.
* main_phase1.py : Simple script runner for standard python environments.
* models.py : Local model loader for Qwen2.5-1.5B with citation checks.
* rag.py : Retrieval pipeline using ChromaDB, MiniLM embeddings, and BM25.
* web_ui.py : Lightweight web server using Python's built-in http.server.

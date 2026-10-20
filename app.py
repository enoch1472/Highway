"""
app.py - Streamlit GUI for The Zebra Crossing Road Safety Assistant.

Faithfully implements the modern dark interface shown in Design.png:
- Tabbed Navigation: Chat, Interactive Quiz, Rules Catalog, Scenarios.
- Quick prompt pills for one-click questions.
- Legal authority badges (Mandatory MUST vs Advisory SHOULD).
- Collapsible retrieved rules with cosine distance scores.
- Interactive Highway Code Quiz with no time limit.
- Powered by cached offline models (SentenceTransformers + Qwen2.5-1.5B).
"""

import time
import streamlit as st
from rag import RuleRAG
from models import LocalQwenLLM
from assistant import RoadSafetyAssistant
from interactive import QUIZ_QUESTIONS, SCENARIOS

# Set page configuration
st.set_page_config(
    page_title="The Zebra Crossing - Road Safety Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme CSS matching Design.png
st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp {
        background-color: #0d0e11;
        color: #e6e8eb;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Top Header Bar */
    .header-box {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 0 20px 0;
        border-bottom: 1px solid #232730;
        margin-bottom: 24px;
    }
    .header-logo {
        width: 48px;
        height: 48px;
        background: #000;
        border: 2px solid #333842;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 3px;
        padding: 6px;
    }
    .header-stripe {
        width: 4px;
        height: 26px;
        background: #fff;
        border-radius: 1px;
    }
    .header-title h1 {
        font-size: 24px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
    }
    .header-title p {
        font-size: 13px;
        color: #9ca3af;
        margin: 0;
    }

    /* Badges */
    .badge-must {
        background-color: #dc2626;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-should {
        background-color: #d97706;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-guideline {
        background-color: #4b5563;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        display: inline-block;
    }

    /* Assistant Message Card */
    .ai-card {
        background-color: #161920;
        border: 1px solid #232730;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 12px 0 16px 0;
    }
    .ai-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .ai-card-text {
        font-size: 16px;
        line-height: 1.6;
        color: #f3f4f6;
        margin-bottom: 14px;
    }
    .ai-card-meta {
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 12px;
    }

    /* Retrieved Rules Table */
    .retrieved-box {
        background-color: #111317;
        border: 1px solid #232730;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 12px;
    }
    .retrieved-title {
        font-size: 12px;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .rule-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid #1a1e26;
        font-size: 13px;
    }
    .rule-row:last-child {
        border-bottom: none;
    }

    /* Suggestions */
    .sugg-box {
        margin-top: 14px;
        padding-top: 10px;
        border-top: 1px dashed #282f3d;
    }
    .sugg-title {
        color: #10b981;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .sugg-chip {
        display: inline-block;
        background-color: #1e2621;
        border: 1px solid #274e35;
        color: #34d399;
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 12px;
        margin: 3px 4px 3px 0;
    }
</style>
""", unsafe_allow_html=True)


# Cache models in memory across Streamlit reruns
@st.cache_resource(show_spinner="Initializing UK Highway Code Knowledge Base...")
def load_assistant():
    rag = RuleRAG(data_path="data/rules.txt", persist_dir="./chroma_db")
    llm = LocalQwenLLM(model_id="Qwen/Qwen2.5-1.5B-Instruct")
    return RoadSafetyAssistant(rag=rag, llm=llm)


# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_completed" not in st.session_state:
    st.session_state.quiz_completed = False
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}

assistant = load_assistant()

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <div style="background:#000; border:2px solid #333842; border-radius:6px; padding:6px; display:flex; gap:3px;">
            <div style="width:3px; height:20px; background:#fff;"></div>
            <div style="width:3px; height:20px; background:#fff;"></div>
            <div style="width:3px; height:20px; background:#fff;"></div>
        </div>
        <div>
            <h3 style="margin:0; font-size:18px; color:#fff;">The Zebra Crossing</h3>
            <span style="font-size:11px; color:#9ca3af;">UK Road Safety Assistant</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio(
        "Navigation",
        ["Road Safety Chat", "Interactive Safety Quiz", "Rules Catalog", "Road Scenarios"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("**Local Pipeline:**")
    st.caption("• **Retriever:** SentenceTransformers (`all-MiniLM-L6-v2`) + BM25")
    st.caption("• **Vector Store:** ChromaDB (Cosine Distance)")
    st.caption("• **Reasoning:** Local Qwen2.5-1.5B-Instruct")
    st.caption("• **Guardrail:** 0.52 Distance Cutoff")
    st.caption(f"• **Rules Indexed:** {assistant.rag.collection.count()} Highway Code Rules")
    
    st.markdown("---")
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.chat_history = []
        assistant.clear_history()
        st.rerun()


# =============================================================================
# TAB 1: ROAD SAFETY CHAT
# =============================================================================
if mode == "Road Safety Chat":
    st.markdown("""
    <div class="header-box">
        <div class="header-logo">
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
        </div>
        <div class="header-title">
            <h1>Ask any UK road safety question</h1>
            <p>Answers strictly cited from official Highway Code rules • MUST vs SHOULD authority preserved</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick prompt pills
    st.write("**Quick Questions:**")
    p_col1, p_col2, p_col3 = st.columns(3)
    quick_q = None
    with p_col1:
        if st.button("Can I overtake someone stopped at a zebra crossing?", use_container_width=True):
            quick_q = "Can I overtake someone stopped at a zebra crossing?"
    with p_col2:
        if st.button("Flashing amber at a pelican crossing", use_container_width=True):
            quick_q = "The amber light is flashing at a pelican crossing, but nobody is crossing. Can I proceed?"
    with p_col3:
        if st.button("Can a cyclist ride across a toucan crossing?", use_container_width=True):
            quick_q = "Can a cyclist ride across a Toucan crossing?"

    # Display Chat History
    for item in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(item["question"])

        with st.chat_message("assistant"):
            legal_weight = item.get("legal_weight", "GUIDELINE")
            is_conversational = item.get("is_conversational", False)

            if is_conversational:
                badge_html = '<span class="badge-guideline" style="background-color:#059669;">INTERACTIVE CHAT</span>'
            elif legal_weight == "MUST":
                badge_html = '<span class="badge-must">MANDATORY LAW (MUST)</span>'
            elif legal_weight == "SHOULD":
                badge_html = '<span class="badge-should">ADVISORY GUIDANCE (SHOULD)</span>'
            else:
                badge_html = '<span class="badge-guideline">OUT OF DOMAIN</span>'

            card_title = "The Zebra Crossing Assistant" if is_conversational else "Official UK Highway Code Response"

            card_html = f"""
            <div class="ai-card">
                <div class="ai-card-header">
                    <strong style="color: #fff; font-size: 15px;">{card_title}</strong>
                    {badge_html}
                </div>
                <div class="ai-card-text">{item['answer']}</div>
                <div class="ai-card-meta">Model: Qwen2.5-1.5B-Instruct • Response generated in {item.get('elapsed_seconds', 0.0)}s (Timer has no limit)</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

            # Retrieved Rules Card
            retrieved = item.get("retrieved_rules", [])
            if retrieved:
                with st.expander(f"Relevant Rules Retrieved ({len(retrieved)} rules)", expanded=False):
                    for r in retrieved:
                        r_legal = r.get("legal_weight", "SHOULD")
                        r_badge = f'<span class="badge-must">MUST</span>' if r_legal == "MUST" else f'<span class="badge-should">SHOULD</span>'
                        st.markdown(f"""
                        <div class="rule-row">
                            <div>
                                <strong>{r.get('rule_id', 'Unknown')}</strong> &nbsp; {r_badge} &nbsp; 
                                <span style="color:#d1d5db;">{r.get('title', r.get('header', ''))}</span>
                            </div>
                            <div style="color: #9ca3af; font-size: 12px;">Distance: {r.get('distance', 0.0):.3f}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Follow-up Suggestions
            suggestions = item.get("suggestions", [])
            if suggestions:
                st.markdown("**You might also want to ask:**")
                chips_cols = st.columns(len(suggestions))
                for idx, s in enumerate(suggestions):
                    with chips_cols[idx]:
                        if st.button(f"{s}", key=f"sugg_{item['question']}_{idx}", use_container_width=True):
                            quick_q = s

    # User Input
    user_query = st.chat_input("Ask a traffic or Highway Code question...") or quick_q

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Searching Highway Code knowledge base and synthesizing answer (no time limit)..."):
                response = assistant.ask(user_query)

            st.session_state.chat_history.append(response)
            st.rerun()


# =============================================================================
# TAB 2: INTERACTIVE HIGHWAY CODE QUIZ (NO TIME LIMIT)
# =============================================================================
elif mode == "Interactive Safety Quiz":
    st.markdown("""
    <div class="header-box">
        <div class="header-logo">
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
        </div>
        <div class="header-title">
            <h1>Road Safety Knowledge Quiz</h1>
            <p>Test your knowledge on priority, crossings, and signals • <strong>No time limit</strong> — take your time!</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    total_q = len(QUIZ_QUESTIONS)
    curr_idx = st.session_state.quiz_index

    if not st.session_state.quiz_completed and curr_idx < total_q:
        q = QUIZ_QUESTIONS[curr_idx]
        st.progress((curr_idx) / total_q)
        st.subheader(f"Question {curr_idx + 1} of {total_q}")
        st.write(f"### {q['question']}")

        selected = st.radio("Choose the correct option:", q["options"], key=f"quiz_opt_{curr_idx}")

        col_sub, col_skip = st.columns([1, 4])
        with col_sub:
            if st.button("Submit Answer", type="primary"):
                user_choice = selected[0]
                is_correct = (user_choice == q["answer"])
                st.session_state.quiz_answers[curr_idx] = {
                    "user_choice": user_choice,
                    "is_correct": is_correct,
                    "q": q
                }
                if is_correct:
                    st.session_state.quiz_score += 1
                    st.success(f"**Correct!** {q['explanation']} (Authority: {q['rule']})")
                else:
                    st.error(f"**Incorrect.** Option **{q['answer']}** is correct.\n\n{q['explanation']} (Authority: {q['rule']})")

                if curr_idx + 1 < total_q:
                    st.session_state.quiz_index += 1
                    time.sleep(2.5)
                    st.rerun()
                else:
                    st.session_state.quiz_completed = True
                    st.rerun()
    else:
        st.balloons()
        pct = (st.session_state.quiz_score / total_q) * 100
        st.success(f"**Quiz Complete! You scored {st.session_state.quiz_score}/{total_q} ({pct:.0f}%)**")
        if pct >= 80:
            st.info("**Expert Road User!** Outstanding command of the UK Highway Code.")
        else:
            st.info("**Good Job!** Check the Rules Catalog tab to review key road priority rules.")

        if st.button("Retake Quiz", type="primary"):
            st.session_state.quiz_index = 0
            st.session_state.quiz_score = 0
            st.session_state.quiz_completed = False
            st.session_state.quiz_answers = {}
            st.rerun()


# =============================================================================
# TAB 3: OFFICIAL RULES CATALOG
# =============================================================================
elif mode == "Rules Catalog":
    st.markdown("""
    <div class="header-box">
        <div class="header-logo">
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
        </div>
        <div class="header-title">
            <h1>Official UK Highway Code Rules Catalog</h1>
            <p>Browse and search all loaded rules with mandatory vs advisory legal status</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    all_rules = assistant.rag.get_all_rules_summary()

    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("Search rules by keyword or number (e.g. 'zebra', '195', 'cyclist'):")
    with col_filter:
        category = st.selectbox(
            "Category Filter:",
            ["All Rules", "Pedestrian Crossings", "Junctions & Signals", "Roundabouts", "Vulnerable Users", "Speed & Stopping", "Parking & Waiting"]
        )

    cat_keywords = {
        "Pedestrian Crossings": ["crossing", "zebra", "pelican", "puffin", "toucan", "pegasus"],
        "Junctions & Signals": ["junction", "stop line", "give way", "box junction", "traffic light"],
        "Roundabouts": ["roundabout"],
        "Vulnerable Users": ["vulnerable", "pedestrian", "cyclist", "horse", "children"],
        "Speed & Stopping": ["speed", "stopping", "overtaking", "distance"],
        "Parking & Waiting": ["parking", "waiting", "dutch reach", "pavement"]
    }

    filtered_rules = all_rules
    if category != "All Rules":
        keywords = cat_keywords[category]
        filtered_rules = [
            r for r in filtered_rules
            if any(k in r["header"].lower() or k in r["text"].lower() for k in keywords)
        ]

    if search_query:
        sq = search_query.strip().lower()
        filtered_rules = [
            r for r in filtered_rules
            if sq in r["rule_id"].lower() or sq in r["title"].lower() or sq in r["text"].lower()
        ]

    st.write(f"Showing **{len(filtered_rules)}** rules:")
    for r in filtered_rules:
        is_must = r.get("legal_weight") == "MUST"
        badge = "MUST" if is_must else "SHOULD"
        with st.expander(f"{r['rule_id']}: {r['title']} - [{badge}]"):
            st.markdown(f"**Legal Authority:** {'Mandatory Legal Requirement (Road Traffic Act)' if is_must else 'Advisory Guidance (Highway Code Best Practice)'}")
            st.write(r["text"])


# =============================================================================
# TAB 4: ROAD SCENARIOS
# =============================================================================
elif mode == "Road Scenarios":
    st.markdown("""
    <div class="header-box">
        <div class="header-logo">
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
            <div class="header-stripe"></div>
        </div>
        <div class="header-title">
            <h1>Hazard Perception & Decision Scenarios</h1>
            <p>'What Would You Do?' real-world driving situations • No time limit</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for sc in SCENARIOS:
        st.markdown(f"### {sc['title']}")
        st.info(sc['situation'])
        st.write(f"**Question:** {sc['question']}")

        choice = st.radio("Choose your action:", sc["choices"], key=f"scenario_{sc['id']}")
        if st.button(f"Confirm Decision for Scenario {sc['id']}", key=f"btn_sc_{sc['id']}"):
            choice_num = choice.split(".")[0].strip()
            if choice_num == sc["best_choice"]:
                st.success("**Top Choice!** Safe, legal, and considerate road practice.")
            else:
                st.warning(f"**Caution:** Option {sc['best_choice']} is the safest legal choice.")
            st.write(f"**Coaching:** {sc['coaching']}")
            st.caption(f"Rules Involved: {', '.join(sc['rules_applied'])}")
        st.markdown("---")

"""
web_ui.py - Zero-Dependency Interactive Web UI for The Zebra Crossing Assistant.

Faithfully implements the modern dark UI shown in Design.png:
- Tabbed interface: Chat, Rules Catalog, and Interactive Quiz.
- Quick prompt pills for one-click questions.
- Legal authority badges (MUST in red, SHOULD in amber).
- Collapsible retrieved rules with cosine distance scores.
- Interactive Highway Code Quiz with instant scoring.
- Runs on Python's built-in http.server (no external web frameworks required).
"""

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from assistant import RoadSafetyAssistant
from interactive import QUIZ_QUESTIONS, SCENARIOS


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Zebra Crossing - Road Safety Assistant</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: #0d0e11;
      color: #e6e8eb;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      height: 100vh;
      display: flex;
      overflow: hidden;
    }
    /* Sidebar */
    .sidebar {
      width: 270px;
      background: #14161b;
      border-right: 1px solid #232730;
      display: flex;
      flex-direction: column;
      padding: 24px 18px;
      gap: 20px;
    }
    .logo-box {
      display: flex;
      align-items: center;
      gap: 14px;
      padding-bottom: 20px;
      border-bottom: 1px solid #232730;
    }
    .logo-icon {
      width: 44px;
      height: 44px;
      background: #000;
      border: 2px solid #333842;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      padding: 6px;
    }
    .zebra-stripes {
      display: flex;
      gap: 3px;
      width: 100%;
      height: 100%;
      align-items: center;
      justify-content: center;
    }
    .stripe {
      width: 4px;
      height: 22px;
      background: #fff;
      border-radius: 1px;
    }
    .logo-text h1 {
      font-size: 17px;
      font-weight: 700;
      color: #fff;
      line-height: 1.2;
    }
    .sidebar-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #1a1e26;
      color: #c9d1d9;
      border: 1px solid #2b313d;
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      text-align: left;
      width: 100%;
    }
    .sidebar-btn:hover {
      background: #232936;
      border-color: #f59e0b;
      color: #fff;
    }
    .sidebar-btn.active {
      background: #2b313e;
      border-color: #f59e0b;
      color: #f59e0b;
    }
    .sidebar-footer {
      margin-top: auto;
      font-size: 11px;
      color: #6b7280;
      text-align: center;
      line-height: 1.4;
    }

    /* Main Area */
    .main {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
      background: #0d0e11;
    }
    .top-nav {
      height: 60px;
      border-bottom: 1px solid #232730;
      display: flex;
      align-items: center;
      padding: 0 28px;
      gap: 28px;
      background: #111317;
    }
    .nav-tab {
      background: none;
      border: none;
      color: #8b949e;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      padding: 18px 4px;
      position: relative;
    }
    .nav-tab.active {
      color: #f59e0b;
    }
    .nav-tab.active::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: #f59e0b;
    }
    .tab-content {
      flex: 1;
      display: none;
      flex-direction: column;
      overflow-y: auto;
      padding: 24px 32px;
    }
    .tab-content.active {
      display: flex;
    }

    /* Chat Tab */
    .chat-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      max-width: 960px;
      width: 100%;
      margin: 0 auto;
      overflow-y: auto;
      gap: 20px;
      padding-bottom: 20px;
    }
    .page-title {
      font-size: 22px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 6px;
    }
    .quick-prompts {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-bottom: 16px;
    }
    .pill {
      background: #161920;
      border: 1px solid #282f3d;
      color: #f59e0b;
      padding: 14px 16px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      line-height: 1.4;
      text-align: left;
    }
    .pill:hover {
      background: #1e232e;
      border-color: #f59e0b;
      transform: translateY(-1px);
    }
    .messages-list {
      display: flex;
      flex-direction: column;
      gap: 20px;
      flex: 1;
    }
    .msg-row {
      display: flex;
      gap: 14px;
      align-items: flex-start;
    }
    .avatar {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: #232730;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      flex-shrink: 0;
    }
    .avatar.user { background: #3b4252; color: #eceff4; }
    .avatar.ai { background: #d97706; color: #fff; }
    .bubble {
      flex: 1;
      background: #161920;
      border: 1px solid #232730;
      border-radius: 12px;
      padding: 18px 22px;
      position: relative;
    }
    .user-bubble {
      background: #1c212b;
      border-color: #2b3342;
    }
    .bubble-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .badge {
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }
    .badge.must { background: #dc2626; color: #fff; }
    .badge.should { background: #d97706; color: #fff; }
    .badge.guideline { background: #4b5563; color: #fff; }
    .bubble-text {
      font-size: 15px;
      line-height: 1.6;
      color: #e5e7eb;
      margin-bottom: 12px;
    }
    .meta-footer {
      font-size: 12px;
      color: #9ca3af;
      margin-bottom: 14px;
    }
    .rules-card {
      background: #111317;
      border: 1px solid #232730;
      border-radius: 8px;
      padding: 12px 16px;
      margin-top: 10px;
    }
    .rules-card-title {
      font-size: 12px;
      font-weight: 600;
      color: #9ca3af;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .rule-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 0;
      border-bottom: 1px solid #1a1e26;
      font-size: 13px;
    }
    .rule-item:last-child { border-bottom: none; }
    .rule-item-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .suggestions-box {
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px dashed #282f3d;
      font-size: 13px;
    }
    .suggestions-title {
      color: #10b981;
      font-weight: 600;
      margin-bottom: 6px;
    }
    .suggestion-chip {
      display: inline-block;
      background: #1e2621;
      border: 1px solid #274e35;
      color: #34d399;
      padding: 4px 10px;
      border-radius: 14px;
      margin: 3px 4px 3px 0;
      cursor: pointer;
      font-size: 12px;
    }
    .suggestion-chip:hover {
      background: #274e35;
      color: #fff;
    }

    /* Input Box */
    .input-bar {
      max-width: 960px;
      width: 100%;
      margin: 0 auto;
      padding: 14px 0 20px 0;
      display: flex;
      gap: 12px;
    }
    .chat-input {
      flex: 1;
      background: #161920;
      border: 1px solid #2b313e;
      border-radius: 10px;
      padding: 14px 18px;
      color: #fff;
      font-size: 15px;
      outline: none;
      transition: border-color 0.2s;
    }
    .chat-input:focus { border-color: #f59e0b; }
    .send-btn {
      background: #f59e0b;
      color: #000;
      border: none;
      border-radius: 10px;
      padding: 0 24px;
      font-weight: 600;
      font-size: 15px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .send-btn:hover { background: #d97706; }

    /* Rules Tables */
    .data-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      background: #14161b;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #232730;
    }
    .data-table th, .data-table td {
      padding: 14px 16px;
      text-align: left;
      border-bottom: 1px solid #232730;
      font-size: 14px;
    }
    .data-table th { background: #1a1e26; color: #9ca3af; font-weight: 600; }

    /* Quiz Tab */
    .quiz-card {
      background: #161920;
      border: 1px solid #2b313e;
      border-radius: 12px;
      padding: 24px;
      max-width: 760px;
      margin: 0 auto;
      width: 100%;
    }
    .quiz-opt-btn {
      display: block;
      width: 100%;
      text-align: left;
      padding: 14px 18px;
      background: #1a1e26;
      border: 1px solid #2b313e;
      border-radius: 8px;
      color: #e5e7eb;
      font-size: 14px;
      margin-top: 10px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .quiz-opt-btn:hover { background: #232936; border-color: #f59e0b; }
  </style>
</head>
<body>

  <!-- Sidebar -->
  <div class="sidebar">
    <div class="logo-box">
      <div class="logo-icon">
        <div class="zebra-stripes">
          <div class="stripe"></div>
          <div class="stripe"></div>
          <div class="stripe"></div>
          <div class="stripe"></div>
        </div>
      </div>
      <div class="logo-text">
        <h1>The Zebra<br>Crossing</h1>
      </div>
    </div>

    <button class="sidebar-btn active" onclick="switchTab('chat')">Road Safety Chat</button>
    <button class="sidebar-btn" onclick="switchTab('quiz')">Take Safety Quiz</button>
    <button class="sidebar-btn" onclick="switchTab('rules')">Rules Catalog</button>

    <div class="sidebar-footer">
      UK Highway Code RAG Assistant<br>
      Qwen2.5-1.5B & ChromaDB Offline
    </div>
  </div>

  <!-- Main Area -->
  <div class="main">
    <div class="top-nav">
      <button class="nav-tab active" id="tab-btn-chat" onclick="switchTab('chat')">Chat</button>
      <button class="nav-tab" id="tab-btn-quiz" onclick="switchTab('quiz')">Interactive Quiz</button>
      <button class="nav-tab" id="tab-btn-rules" onclick="switchTab('rules')">Rules Catalog</button>
    </div>

    <!-- CHAT TAB -->
    <div class="tab-content active" id="tab-chat">
      <div class="chat-container">
        <div class="page-title">Ask any UK road safety question</div>

        <div class="quick-prompts">
          <div class="pill" onclick="sendPrompt('Can I overtake someone stopped at a zebra crossing?')">
            Can I overtake someone stopped at a zebra crossing?
          </div>
          <div class="pill" onclick="sendPrompt('Flashing amber at a pelican crossing')">
            Flashing amber at a pelican crossing
          </div>
          <div class="pill" onclick="sendPrompt('Can a cyclist ride across a toucan crossing?')">
            Can a cyclist ride across a toucan crossing?
          </div>
        </div>

        <div class="messages-list" id="chat-messages">
          <!-- Initial Welcome Message -->
          <div class="msg-row">
            <div class="avatar ai">ZC</div>
            <div class="bubble">
              <div class="bubble-header">
                <strong>The Zebra Crossing Assistant</strong>
                <span class="badge guideline">OFFICIAL HIGHWAY CODE</span>
              </div>
              <div class="bubble-text">
                Welcome! I am your interactive assistant for the UK Highway Code and road safety rules.
                You can ask me anything about pedestrian crossings, priority at junctions, speed limits, or rules for cyclists and drivers.
              </div>
            </div>
          </div>
        </div>

        <div class="input-bar">
          <input type="text" id="user-input" class="chat-input" placeholder="Ask a traffic question..." onkeydown="if(event.key==='Enter') doSend()">
          <button class="send-btn" onclick="doSend()">Ask</button>
        </div>
      </div>
    </div>

    <!-- QUIZ TAB -->
    <div class="tab-content" id="tab-quiz">
      <div class="page-title">Interactive Road Safety Quiz</div>
      <p style="color: #9ca3af; margin-bottom: 20px;">Test your knowledge on priority, signs, and crossing rules.</p>
      <div id="quiz-container" class="quiz-card">
        <div id="quiz-question-box">
          <h3 id="quiz-q-title" style="margin-bottom: 16px;">Loading quiz...</h3>
          <div id="quiz-options"></div>
        </div>
        <div id="quiz-feedback" style="display:none; margin-top: 18px; padding: 14px; border-radius: 8px;"></div>
        <button id="quiz-next-btn" class="send-btn" style="margin-top: 16px; display: none;" onclick="nextQuiz()">Next Question</button>
      </div>
    </div>

    <!-- RULES CATALOG TAB -->
    <div class="tab-content" id="tab-rules">
      <div class="page-title">Official Rules Catalog</div>
      <p style="color: #9ca3af;">All loaded rules from the UK Highway Code knowledge base.</p>
      <input type="text" id="rule-search-box" class="chat-input" style="margin-top: 14px; max-width: 400px;" placeholder="Filter rules by keyword..." oninput="filterRules()">
      <table class="data-table" id="rules-table">
        <thead>
          <tr>
            <th width="120">Rule ID</th>
            <th width="120">Legal Weight</th>
            <th>Title & Requirement</th>
          </tr>
        </thead>
        <tbody id="rules-table-body">
          <tr><td colspan="3">Loading rules...</td></tr>
        </tbody>
      </table>
    </div>

  </div>

  <script>
    let currentQuizIndex = 0;
    let quizData = [];
    let quizScore = 0;

    function switchTab(tabName) {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));

      const tabBtn = document.getElementById('tab-btn-' + tabName);
      if (tabBtn) tabBtn.classList.add('active');
      const content = document.getElementById('tab-' + tabName);
      if (content) content.classList.add('active');

      if (tabName === 'rules') loadRulesCatalog();
      if (tabName === 'quiz') startQuiz();
    }

    function sendPrompt(text) {
      document.getElementById('user-input').value = text;
      doSend();
    }

    async function doSend() {
      const input = document.getElementById('user-input');
      const question = input.value.trim();
      if (!question) return;
      input.value = '';

      const container = document.getElementById('chat-messages');

      // Add user message
      const userHtml = `
        <div class="msg-row">
          <div class="avatar user">U</div>
          <div class="bubble user-bubble">
            <div class="bubble-text">${question}</div>
          </div>
        </div>`;
      container.innerHTML += userHtml;

      // Add loading placeholder
      const loadingId = 'ai-loading-' + Date.now();
      container.innerHTML += `
        <div class="msg-row" id="${loadingId}">
          <div class="avatar ai">ZC</div>
          <div class="bubble">
            <div class="bubble-text">Searching official Highway Code rules and generating answer...</div>
          </div>
        </div>`;
      container.scrollTop = container.scrollHeight;

      try {
        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question })
        });
        const data = await res.json();

        const badgeClass = data.legal_weight === 'MUST' ? 'must' : (data.legal_weight === 'SHOULD' ? 'should' : 'guideline');
        const badgeLabel = data.legal_weight === 'MUST' ? 'MANDATORY (MUST)' : (data.legal_weight === 'SHOULD' ? 'ADVISORY (SHOULD)' : 'OUT OF DOMAIN');

        let rulesHtml = '';
        if (data.retrieved_rules && data.retrieved_rules.length > 0) {
          rulesHtml = `<div class="rules-card"><div class="rules-card-title">Relevant Rules Retrieved</div>`;
          for (const r of data.retrieved_rules) {
            const rBadge = r.legal_weight === 'MUST' ? '<span class="badge must">MUST</span>' : '<span class="badge should">SHOULD</span>';
            rulesHtml += `
              <div class="rule-item">
                <div class="rule-item-left">
                  <strong>${r.rule_id}</strong>
                  ${rBadge}
                  <span>${r.title || r.header}</span>
                </div>
                <div style="color: #9ca3af; font-size: 12px;">dist: ${r.distance}</div>
              </div>`;
          }
          rulesHtml += `</div>`;
        }

        let suggestionsHtml = '';
        if (data.suggestions && data.suggestions.length > 0) {
          suggestionsHtml = `<div class="suggestions-box"><div class="suggestions-title">You might also want to ask:</div>`;
          for (const s of data.suggestions) {
            suggestionsHtml += `<span class="suggestion-chip" onclick="sendPrompt('${s.replace(/'/g, "\\'")}')">${s}</span>`;
          }
          suggestionsHtml += `</div>`;
        }

        const aiBubbleHtml = `
          <div class="avatar ai">ZC</div>
          <div class="bubble">
            <div class="bubble-header">
              <strong>The Zebra Crossing Assistant</strong>
              <span class="badge ${badgeClass}">${badgeLabel}</span>
            </div>
            <div class="bubble-text">${data.answer}</div>
            <div class="meta-footer">Model: Qwen2.5-1.5B-Instruct • Generated in ${data.elapsed_seconds}s</div>
            ${rulesHtml}
            ${suggestionsHtml}
          </div>`;

        document.getElementById(loadingId).innerHTML = aiBubbleHtml;
      } catch (err) {
        document.getElementById(loadingId).innerHTML = `
          <div class="avatar ai">ZC</div>
          <div class="bubble"><div class="bubble-text" style="color: #ef4444;">Error connecting to assistant: ${err}</div></div>`;
      }
      container.scrollTop = container.scrollHeight;
    }

    async function loadRulesCatalog() {
      try {
        const res = await fetch('/api/rules');
        window.allRules = await res.json();
        renderRules(window.allRules);
      } catch (e) {
        document.getElementById('rules-table-body').innerHTML = `<tr><td colspan="3">Failed to load rules.</td></tr>`;
      }
    }

    function renderRules(rules) {
      const tbody = document.getElementById('rules-table-body');
      tbody.innerHTML = '';
      for (const r of rules) {
        const badge = r.legal_weight === 'MUST' ? '<span class="badge must">MUST</span>' : '<span class="badge should">SHOULD</span>';
        tbody.innerHTML += `
          <tr>
            <td><strong>${r.rule_id}</strong></td>
            <td>${badge}</td>
            <td><strong>${r.title}</strong><br><span style="color:#9ca3af; font-size:12px;">${r.text.replace(/\\n/g, ' ').slice(0, 140)}...</span></td>
          </tr>`;
      }
    }

    function filterRules() {
      const q = document.getElementById('rule-search-box').value.toLowerCase();
      if (!window.allRules) return;
      const filtered = window.allRules.filter(r => r.rule_id.toLowerCase().includes(q) || r.title.toLowerCase().includes(q) || r.text.toLowerCase().includes(q));
      renderRules(filtered);
    }

    async function startQuiz() {
      const res = await fetch('/api/quiz');
      quizData = await res.json();
      currentQuizIndex = 0;
      quizScore = 0;
      showQuizQuestion();
    }

    function showQuizQuestion() {
      const q = quizData[currentQuizIndex];
      document.getElementById('quiz-q-title').innerText = `Question ${currentQuizIndex + 1} of ${quizData.length}: ${q.question}`;
      const optBox = document.getElementById('quiz-options');
      optBox.innerHTML = '';
      q.options.forEach((opt, idx) => {
        const letter = String.fromCharCode(65 + idx);
        optBox.innerHTML += `<button class="quiz-opt-btn" onclick="submitQuizAnswer('${letter}')">${opt}</button>`;
      });
      document.getElementById('quiz-feedback').style.display = 'none';
      document.getElementById('quiz-next-btn').style.display = 'none';
    }

    function submitQuizAnswer(letter) {
      const q = quizData[currentQuizIndex];
      const isCorrect = letter === q.answer;
      if (isCorrect) quizScore++;

      const feedback = document.getElementById('quiz-feedback');
      feedback.style.display = 'block';
      if (isCorrect) {
        feedback.style.background = '#132e22';
        feedback.style.border = '1px solid #10b981';
        feedback.innerHTML = `<strong style="color: #34d399;">[Correct!]</strong><br>${q.explanation} (Official Ref: ${q.rule})`;
      } else {
        feedback.style.background = '#301c1c';
        feedback.style.border = '1px solid #ef4444';
        feedback.innerHTML = `<strong style="color: #f87171;">[Incorrect] (Option ${q.answer} was correct).</strong><br>${q.explanation} (Official Ref: ${q.rule})`;
      }
      document.getElementById('quiz-next-btn').style.display = 'block';
    }

    function nextQuiz() {
      currentQuizIndex++;
      if (currentQuizIndex < quizData.length) {
        showQuizQuestion();
      } else {
        const pct = Math.round((quizScore / quizData.length) * 100);
        document.getElementById('quiz-question-box').innerHTML = `
          <h3>Quiz Finished!</h3>
          <p style="font-size: 18px; margin-top: 10px;">Your score: <strong>${quizScore}/${quizData.length} (${pct}%)</strong></p>
          <p style="color: #9ca3af; margin-top: 6px;">${pct >= 80 ? 'Outstanding Highway Code Knowledge!' : 'Good effort! Review the rules to improve.'}</p>
          <button class="send-btn" style="margin-top: 16px;" onclick="startQuiz()">Retake Quiz</button>`;
        document.getElementById('quiz-feedback').style.display = 'none';
        document.getElementById('quiz-next-btn').style.display = 'none';
      }
    }
  </script>
</body>
</html>
"""


class ZebraCrossingWebHandler(BaseHTTPRequestHandler):
    assistant: Optional[RoadSafetyAssistant] = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Serve the single-page HTML interface
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        # API endpoint to fetch all loaded Highway Code rules
        if parsed.path == "/api/rules":
            rules = self.assistant.rag.get_all_rules_summary()
            self._send_json(rules)
            return

        # API endpoint to fetch quiz questions
        if parsed.path == "/api/quiz":
            self._send_json(QUIZ_QUESTIONS)
            return

        self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/ask":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                question = data.get("question", "")
                response = self.assistant.ask(question)
                self._send_json(response)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        self.send_error(404, "Endpoint Not Found")

    def _send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def launch_web_ui(assistant: RoadSafetyAssistant, port: int = 7860):
    """Starts the zero-dependency web interface."""
    ZebraCrossingWebHandler.assistant = assistant
    server = HTTPServer(("127.0.0.1", port), ZebraCrossingWebHandler)
    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 78)
    print("THE ZEBRA CROSSING INTERACTIVE WEB UI IS RUNNING")
    print(f"Open in your browser: {url}")
    print("=" * 78 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb server stopped.")

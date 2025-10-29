from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file, Response
from graph import ResearchGraph
from datetime import datetime
from io import BytesIO
import json
import os

app = Flask(__name__)
G = ResearchGraph()

LOGIN = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>AI Research Assistant — Sign in</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      body{margin:0; font-family:Inter, "Segoe UI", Roboto, Arial; 
           background:linear-gradient(180deg,#0b0b1a,#071026); color:#e6eef6; 
           display:flex; align-items:center; justify-content:center; height:100vh;}
      .card{width:720px; padding:28px; border-radius:14px; 
            background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); 
            border:1px solid rgba(255,255,255,0.03); box-shadow: 0 10px 40px rgba(0,0,0,0.6);}
      h1{margin:0 0 6px 0; font-size:28px; color:#f3f6fb;}
      p{margin:0 0 18px 0; color:#aab0b8;}
      .row{display:flex; gap:12px;}
      input[type="text"]{flex:1;padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.04); 
                         background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); color:inherit;}
      .run-btn{padding:10px 16px;border-radius:10px;border:none;background:linear-gradient(90deg,#8a6cff,#ff6ec7);color:white;font-weight:600;cursor:pointer;box-shadow:0 8px 30px rgba(138,108,255,0.12); transition: transform .12s, box-shadow .12s;}
      .run-btn:hover{ transform: translateY(-4px); box-shadow: 0 22px 60px rgba(138,108,255,0.2); }
      .muted{color:#9aa0a9;font-size:14px;margin-top:12px;}
      .center{display:flex; justify-content:center; margin-top:18px;}
      a.link{color:#9aa0ff;text-decoration:none;}
      @media (max-width:700px){ .card{width:92vw;} }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>AI Research Assistant</h1>
      <p>Enter your name to open your private workspace (history will be tied to this name).</p>

      <form method="get" action="/workspace">
        <div class="row">
          <input name="name" type="text" placeholder="Your name (required)" required />
          <!-- reuse run-btn style so it moves+glows like Run -->
          <button class="run-btn" type="submit">Enter workspace</button>
        </div>
      </form>

      <div class="muted">
        This demo stores session history locally on the server (state.json) and ties entries to the name you enter.
      </div>

      <div class="center" style="margin-top:22px">
        <small style="color:#8f95a0">Need a quick test name? Try <a class="link" href="/workspace?name=demo">demo</a></small>
      </div>
    </div>
  </body>
</html>
"""

WORKSPACE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>AI Research Assistant — Workspace</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      :root{
        --bg-top: #0b0b1a; --bg-bot: #071026; --muted: #9ea6b0; --text: #eaf1ff;
        --accent-start: #8a6cff; --accent-end: #ff6ec7; --card-border: rgba(255,255,255,0.035);
      }
      html,body{height:100%;margin:0;background:radial-gradient(1200px 600px at 10% 10%, rgba(138,108,255,0.06), transparent 10%), linear-gradient(180deg,var(--bg-top),var(--bg-bot)); color:var(--text); font-family:Inter, "Segoe UI", Roboto, Arial, sans-serif;}
      .app{display:flex;height:100vh;gap:28px;}
      .sidebar{width:260px;padding:26px;box-sizing:border-box;background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.02));border-right:1px solid var(--card-border);display:flex;flex-direction:column;gap:18px;}
      .brand{font-weight:700;color:var(--accent-start);display:flex;align-items:center;gap:12px;}
      .logo{width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,var(--accent-start),var(--accent-end));display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;box-shadow: 0 12px 30px rgba(138,108,255,0.12); font-size:16px;}
      nav{margin-top:6px;display:flex;flex-direction:column;gap:8px;}
      .nav-item{padding:12px 14px;border-radius:10px;color:var(--muted);cursor:pointer; transition:0.18s;}
      .nav-item.active{ background: rgba(138,108,255,0.04); color:var(--text); border-left:3px solid var(--accent-start); padding-left:11px; box-shadow: inset 0 -6px 18px rgba(0,0,0,0.3); }
      .recent-header { margin-top:12px; color:var(--muted); font-size:13px; }
      .recent-list{margin-top:10px;display:flex;flex-direction:column;gap:8px;}
      .recent-item { cursor:pointer; padding:4px 0; color:#cfd4ff; transition:0.12s; font-size:13px; opacity:0.95; }
      .recent-item:hover { color:#fff; transform: translateX(4px); }

      .main{flex:1;padding:28px;box-sizing:border-box;overflow:auto;}
      .topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px;}
      .title{font-size:28px;font-weight:700;letter-spacing:0.2px;}
      .subtitle{color:var(--muted); margin-top:6px;}

      .controls{display:flex;align-items:center;gap:12px;}
      .user-badge{padding:8px 12px;border-radius:10px;border:1px solid var(--card-border); background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.02)); color:var(--text); font-weight:600;}

      .panel{background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.008));border-radius:14px;padding:18px;box-shadow: 0 12px 40px rgba(6,8,12,0.6);border:1px solid var(--card-border);}
      .input-row{display:flex;gap:12px;align-items:center;width:100%;margin-bottom:18px;}
      .query-input{flex:1;padding:14px 16px;border-radius:12px;border:1px solid rgba(255,255,255,0.03);background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); color:var(--text);font-size:15px;box-shadow: inset 0 -6px 30px rgba(0,0,0,0.5);}
      .run-btn{padding:10px 18px;border-radius:12px;border:none;cursor:pointer;background: linear-gradient(90deg,var(--accent-start),var(--accent-end));color:white;font-weight:700;box-shadow: 0 14px 40px rgba(138,108,255,0.14); transition: transform .12s, box-shadow .12s;}
      .run-btn:hover{ transform: translateY(-4px); box-shadow: 0 28px 80px rgba(138,108,255,0.24); }

      .result-grid{display:grid;grid-template-columns:1fr;gap:18px;margin-top:10px;}
      .card-title{color:var(--accent-start);font-weight:700;margin-bottom:8px;}
      .summary-box{background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.02)); padding:18px;border-radius:12px;color:var(--text);min-height:120px;border:1px solid rgba(255,255,255,0.02); box-shadow: 0 8px 30px rgba(4,6,12,0.6);}

      .docs-list{margin-top:10px;display:flex;flex-direction:column;gap:12px;}
      .doc-item{padding:12px;border-radius:12px;background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.02)); border:1px solid rgba(255,255,255,0.02); transition: 0.18s; box-shadow: 0 6px 18px rgba(0,0,0,0.5);}
      .doc-item:hover{ transform: translateY(-6px); box-shadow: 0 22px 60px rgba(138,108,255,0.08), 0 6px 18px rgba(0,0,0,0.6); border-color: rgba(138,108,255,0.12); }
      .doc-title{color:#eaf1ff;font-weight:700;font-size:14px;}
      .doc-snippet{color:var(--muted);font-size:13px;}

      .history-entry{padding:12px;border-radius:10px;background: linear-gradient(90deg, rgba(255,255,255,0.01), rgba(0,0,0,0.03));border:1px solid rgba(255,255,255,0.02); transition:0.15s;}
      .history-entry:hover{ transform: translateY(-6px); box-shadow: 0 18px 48px rgba(138,108,255,0.06); }

      .switch { position: relative; display:inline-block; width:48px; height:26px; margin-left:8px; }
      .switch input { display:none; }
      .slider { position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0; background: rgba(255,255,255,0.05); transition: .3s; border-radius:999px; }
      .slider:before { position:absolute; content:""; height:20px; width:20px; left:3px; top:3px; background-color:#fff; border-radius:50%; transition: .3s; box-shadow: 0 8px 20px rgba(0,0,0,0.6); }
      input:checked + .slider { background: linear-gradient(90deg,var(--accent-start),var(--accent-end)); box-shadow: 0 14px 40px rgba(138,108,255,0.12); }
      input:checked + .slider:before { transform: translateX(22px); }

      @media (max-width:900px){ .sidebar{display:none} .app{flex-direction:column} .main{padding:18px} }
      input:focus, textarea:focus{outline:none; box-shadow:0 0 0 6px rgba(138,108,255,0.04); border-color:rgba(138,108,255,0.18); }
      /* small style for rendered HTML inside summary box */
      .summary-box p { margin: 0 0 10px 0; line-height:1.45; color:var(--text); }
      .summary-box strong { color: white; }
    </style>
  </head>
  <body>
    <div class="app">
      <div class="sidebar panel">
        <div class="brand"><div class="logo">AI</div> <div>Workspace</div></div>
        <nav>
          <div class="nav-item active" id="nav-home" onclick="selectNav('home')">Home</div>
          <div class="nav-item" id="nav-history" onclick="selectNav('history')">History</div>
          <!-- Profile removed -->
          <div class="nav-item" onclick="exportPdf()">Export</div>
        </nav>

        <div class="recent-header">Recent</div>
        <div class="recent-list" id="recent-list"></div>
        <div style="flex:1"></div>
        <div style="color:var(--muted); font-size:13px">Signed in as</div>
        <div style="font-weight:700; color:var(--text); margin-top:6px" id="signed-name">{{ name|e }}</div>
        <div style="margin-top:10px">
          <a class="run-btn" href="/">Logout</a>
        </div>
      </div>

      <div class="main">
        <div class="topbar">
          <div>
            <div class="title">AI Research Assistant</div>
            <div class="subtitle">Ask questions, get concise summaries and short implementation plans.</div>
          </div>

          <div class="controls">
            <div style="color:var(--muted); margin-right:8px">Name:</div>
            <div class="user-badge">{{ name|e }}</div>

            <div style="display:flex; align-items:center; margin-left:12px;">
              <div style="color:var(--muted); font-size:14px; margin-right:8px;">LLM Mode</div>
              <label class="switch" title="Toggle LLM-only mode">
                <input id="chat_mode" type="checkbox" />
                <span class="slider"></span>
              </label>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="input-row">
            <input id="q" class="query-input" type="text" placeholder="Ask anything — example: 'How to build a demo using LangGraph'">
            <button class="run-btn" id="run_btn" onclick="run()">Run</button>
          </div>

          <div class="result-grid" id="results-area">
            <div class="panel" id="summary-panel">
              <div class="card-title">Summary</div>
              <!-- summary-box will receive innerHTML (markdown -> html) -->
              <div class="summary-box" id="summary-box">No results yet. Run a query to see a concise summary and plan.</div>
            </div>

            <div class="panel" id="plan-panel" style="display:none;">
              <div class="card-title">Plan</div>
              <div id="plan-box" class="summary-box"></div>
            </div>

            <div class="panel" id="docs-panel" style="display:none;">
              <div class="card-title">Documents used</div>
              <div class="docs-list" id="docs-list"></div>
            </div>
          </div>

          <div class="history-panel" id="history-panel" style="display:none;">
            <div class="card-title">Session history</div>
            <div id="history-entries"></div>
          </div>

        </div>

      </div>
    </div>

    <script>
      // Workspace page script
      const NAME = "{{ name|e }}";

      // helper: convert simple markdown bold **text** to HTML <strong>text</strong>
      function mdToHtml(text){
        if(!text) return "";
        // escape then replace bold markers. simple approach:
        const esc = String(text)
          .replaceAll('&','&amp;')
          .replaceAll('<','&lt;')
          .replaceAll('>','&gt;')
          .replaceAll('"','&quot;');
        // replace **bold** with <strong>...</strong> (supports multiple)
        const bolded = esc.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // convert double newlines to paragraph breaks, single newline to <br>
        const para = bolded.replace(/\\r\\n|\\r/g,'\\n').split('\\n\\n').map(p => p.replace(/\\n/g, '<br/>')).map(p => '<p>' + p + '</p>').join('');
        return para;
      }

      document.addEventListener('DOMContentLoaded', () => {
        const lastq = localStorage.getItem('rga_lastq');
        if (lastq) document.getElementById('q').value = lastq;
        refreshRecent();
        showHistory();
        document.getElementById('q').focus();
      });

      function selectNav(id){
        document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
        document.getElementById('nav-'+id).classList.add('active');
        if (id === 'history'){
          document.getElementById('history-panel').style.display = 'block';
          document.getElementById('docs-panel').style.display = 'none';
          document.getElementById('plan-panel').style.display = 'none';
        } else {
          document.getElementById('history-panel').style.display = 'none';
          document.getElementById('docs-panel').style.display = 'block';
          document.getElementById('plan-panel').style.display = 'block';
        }
      }

      async function run(){
        const q = document.getElementById('q').value.trim();
        const chatMode = document.getElementById('chat_mode').checked;
        const name = NAME;
        if (!name){ alert('Name required — go back to login.'); return; }
        if (!q){ alert('Please enter a query.'); return; }

        document.getElementById('summary-box').innerHTML = '<p>Thinking...</p>';
        document.getElementById('plan-panel').style.display = 'none';
        document.getElementById('docs-panel').style.display = 'none';
        localStorage.setItem('rga_lastq', q);

        try {
          const res = await fetch('/api/run', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ session_id: name, query: q, chat_mode: chatMode, user_name: name })
          });
          const j = await res.json();
          // convert markdown bold to HTML and insert as innerHTML
          document.getElementById('summary-box').innerHTML = mdToHtml(j.summary || 'No summary returned.');
          if (j.plan && j.plan.plan){
            document.getElementById('plan-box').innerHTML = mdToHtml(j.plan.plan);
            document.getElementById('plan-panel').style.display = 'block';
          } else {
            document.getElementById('plan-panel').style.display = 'none';
          }
          if (j.docs && j.docs.length){
            const dl = document.getElementById('docs-list'); dl.innerHTML = '';
            j.docs.forEach(d=>{
              const el = document.createElement('div'); el.className='doc-item';
              const title = document.createElement('div'); title.className='doc-title';
              if (d.url){ title.innerHTML = `<a href="${escapeHtml(d.url)}" target="_blank" style="color:inherit;text-decoration:none">${escapeHtml(d.title || d.id)}</a>`; }
              else { title.textContent = d.title || d.id; }
              const snip = document.createElement('div'); snip.className='doc-snippet'; snip.textContent = (d.text || '').slice(0,220);
              el.appendChild(title); el.appendChild(snip); dl.appendChild(el);
            });
            document.getElementById('docs-panel').style.display = 'block';
          } else {
            document.getElementById('docs-panel').style.display = 'none';
          }
          addRecentLocal(q);
          await refreshRecent();
          await showHistory();
        } catch (err){
          let msg = 'Error: ' + (err.message || 'Request failed');
          document.getElementById('summary-box').innerHTML = mdToHtml(msg);
        }
      }

      function escapeHtml(unsafe){ if (unsafe===null||unsafe===undefined) return ''; return String(unsafe).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'); }

      function addRecentLocal(q){
        const key='rga_recent_local';
        let arr = JSON.parse(localStorage.getItem(key)||'[]');
        arr = arr.filter(x=>x!==q);
        arr.unshift(q);
        if(arr.length>20) arr.pop();
        localStorage.setItem(key, JSON.stringify(arr));
      }

      async function refreshRecent(){
        const name = NAME;
        const container = document.getElementById('recent-list');
        if (!container) return;
        container.innerHTML = '';
        if (!name) return;
        try {
          const res = await fetch('/api/history?name=' + encodeURIComponent(name));
          if (!res.ok) return;
          const data = await res.json();
          let items = [];
          if (data && typeof data === 'object') {
            Object.values(data).forEach(session => {
              if (session && Array.isArray(session.history)) {
                session.history.forEach(h => {
                  if (h && h.query) items.push(h.query);
                });
              }
            });
          }
          if (!items || items.length === 0) return;
          const seen = new Set();
          const unique = [];
          for (let i = items.length - 1; i >= 0; i--){
            const q = items[i];
            if (!seen.has(q)){
              seen.add(q);
              unique.push(q);
            }
          }
          unique.reverse();
          const top = unique.slice(0, 10);
          top.forEach(q => {
            const el = document.createElement('div');
            el.className = 'recent-item';
            el.textContent = q;
            el.onclick = () => { document.getElementById('q').value = q; };
            container.appendChild(el);
          });
        } catch (err){
          console.error('refreshRecent error', err);
        }
      }

      async function showHistory(){
        const name = NAME;
        if (!name) return;
        try {
          const res = await fetch('/api/history?name=' + encodeURIComponent(name));
          if (!res.ok){
            document.getElementById('history-entries').innerHTML = '<div class="meta">No history found for this user.</div>';
            return;
          }
          const data = await res.json();
          renderHistory(data);
        } catch (err){
          document.getElementById('history-entries').innerHTML = '<div class="meta">Unable to load history.</div>';
        }
      }
      function renderHistory(data){
        const container = document.getElementById('history-entries'); container.innerHTML=''; const keys = Object.keys(data||{}); if(keys.length===0){ container.innerHTML='<div class="meta">No history found for this user.</div>'; return; }
        keys.forEach(sid=>{ const session = data[sid]; const hdr = document.createElement('div'); hdr.className='meta'; hdr.textContent='Session: '+sid+' — '+(session.user && session.user.name ? session.user.name : ''); container.appendChild(hdr);
          (session.history||[]).slice().reverse().forEach(entry=>{ const e=document.createElement('div'); e.className='history-entry'; const meta=document.createElement('div'); meta.className='meta'; meta.textContent=entry.timestamp + ' • ' + (entry.mode||''); const q=document.createElement('div'); q.style.fontWeight='700'; q.style.marginTop='6px'; q.textContent=entry.query; const summary=document.createElement('div'); summary.style.marginTop='8px'; summary.innerHTML = mdToHtml((entry.summary||'').slice(0,1000)); e.appendChild(meta); e.appendChild(q); e.appendChild(summary); container.appendChild(e); }); });
      }

      // PDF export: request blob and download
      async function exportPdf(){
        const name = NAME;
        if (!name){ alert('Name required'); return; }
        try {
          const res = await fetch('/api/export_pdf?name=' + encodeURIComponent(name));
          if (!res.ok){
            const txt = await res.text();
            alert('Export failed: ' + txt.slice(0,500));
            return;
          }
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = name + '_history.pdf';
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);
        } catch (err){
          alert('Export error: ' + (err.message || err));
        }
      }

    </script>
  </body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(LOGIN)


@app.route('/workspace')
def workspace():
    name = request.args.get('name', '').strip()
    if not name:
        return redirect(url_for('index'))
    return render_template_string(WORKSPACE, name=name)


@app.route('/api/run', methods=['POST'])
def api_run():
    body = request.get_json() or {}
    session_id = body.get('session_id') or body.get('user_name') or 'user1'
    query = body.get('query', '')
    chat_mode = bool(body.get('chat_mode', False))
    user_name = body.get('user_name', None)
    if not user_name:
        user_name = session_id
    if not query:
        return jsonify({'error': 'missing query'}), 400
    res = G.run(session_id, query, chat_mode=chat_mode, user_name=user_name)
    return jsonify(res)


@app.route('/api/history')
def api_history():
    from graph import load_state
    sid = request.args.get('session_id', None)
    name = request.args.get('name', None)

    if not sid and not name:
        return jsonify({"error": "missing session_id or name parameter"}), 400

    state = load_state()
    sessions = state.get('sessions', {})

    if sid:
        return jsonify(sessions.get(sid, {}))

    if name:
        name_norm = name.strip().lower()
        out = {}
        for s_id, sdata in sessions.items():
            user_meta = sdata.get("user") or {}
            stored_name = (user_meta.get("name") or sdata.get("user_name") or "").strip().lower()
            if s_id.strip().lower() == name_norm or stored_name == name_norm:
                out[s_id] = sdata
        return jsonify(out)

    return jsonify({})


@app.route('/api/export_pdf')
def api_export_pdf():
    """
    Generate a readable PDF containing the user's history.
    Uses reportlab.platypus Paragraph to support basic bold rendering.
    """
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({"error": "missing name parameter"}), 400

    from graph import load_state
    state = load_state()
    sessions = state.get('sessions', {})

    name_norm = name.lower()
    user_sessions = {}
    for s_id, sdata in sessions.items():
        user_meta = sdata.get("user") or {}
        stored_name = (user_meta.get("name") or sdata.get("user_name") or "").strip().lower()
        if s_id.strip().lower() == name_norm or stored_name == name_norm:
            user_sessions[s_id] = sdata

    if not user_sessions:
        return jsonify({"error": "no history found for this user"}), 404

    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT
    except Exception as e:
        return Response("PDF export requires the 'reportlab' package. Install with: pip install reportlab\n\nError: " + str(e), status=501, mimetype='text/plain')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.7*inch, rightMargin=0.7*inch,
                            topMargin=0.7*inch, bottomMargin=0.7*inch)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('Heading1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, spaceAfter=8)
    normal = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, alignment=TA_LEFT)
    small = ParagraphStyle('Small', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12)

    story = []
    story.append(Paragraph(f"AI Research Assistant — History for {name}", h1))
    story.append(Paragraph(f"Exported: {datetime.utcnow().isoformat()}Z", small))
    story.append(Spacer(1, 12))

    import re, html
    def md_to_html_for_pdf(s: str) -> str:
        if not s:
            return ''
        escaped = html.escape(s)
        converted = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
        paragraphs = converted.split('\\n\\n')
        html_parts = []
        for p in paragraphs:
            p = p.replace('\\n', '<br/>')
            html_parts.append(p)
        return '<br/><br/>'.join(html_parts)

    for s_id, sdata in user_sessions.items():
        story.append(Paragraph(f"Session: {s_id}", ParagraphStyle('sesh', parent=h1, fontSize=12)))
        story.append(Spacer(1, 6))
        history = sdata.get('history', [])
        if not history:
            story.append(Paragraph("(no entries)", normal))
            story.append(Spacer(1, 8))
            continue

        for entry in history:
            ts = entry.get('timestamp', '')
            q = entry.get('query', '')
            summary = entry.get('summary') or ''
            q_html = md_to_html_for_pdf(q)
            summary_html = md_to_html_for_pdf(summary)
            story.append(Paragraph(f"<b>{html.escape(ts)}</b> — Query: {q_html}", normal))
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>Summary:</b> {summary_html}", normal))
            story.append(Spacer(1, 8))

        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{name}_history.pdf", mimetype="application/pdf")


if __name__ == '__main__':
    app.run(port=5000, debug=True)

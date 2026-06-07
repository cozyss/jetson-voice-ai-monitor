#!/usr/bin/env python3
import json, html, os, time
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(os.environ.get('VOICE_DASHBOARD_PORT', '7862'))
BASE = Path(os.environ.get('VOICE_AI_BASE', '/workspace/voice-ai'))
STATE_FILE = BASE/'state.json'
QA_FILE = BASE/'qa_review_queue.json'
WEAK_FILE = BASE/'weak_answers.json'
KB_FILE = BASE/'knowledge_base'/'kb_items.json'
COMMANDS_FILE = BASE/'commands.jsonl'


def read_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    tmp.replace(path)

def esc(x):
    return html.escape(str(x if x is not None else ''))

def short(x, n=260):
    x = str(x if x is not None else '')
    return x if len(x) <= n else x[:n-1] + '…'

def state(): return read_json(STATE_FILE, {})
def qa_items(): return read_json(QA_FILE, [])
def weak_items(): return read_json(WEAK_FILE, [])
def kb_items(): return read_json(KB_FILE, [])

def command(action, **kw):
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    rec = {'action': action, **kw, 'ts': time.time()}
    with COMMANDS_FILE.open('a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

def sig(qa, kb):
    last = qa[-1] if qa else {}
    return ':'.join(map(str, [len(qa), len(kb), last.get('id',''), last.get('status',''), 1 if last.get('internet_god_judgment') else 0]))

def status_text(s):
    st = s.get('status') or 'unknown'
    if st == 'idle': return 'Idle / ready'
    if st == 'recording': return 'Recording now'
    if st == 'transcribing': return 'Transcribing voice'
    if st in ('thinking','responding'): return 'Local Jetson Tutor is thinking'
    if st == 'speaking': return 'Speaking final answer'
    if st == 'error': return 'Error'
    return st

def review_section(qa):
    rows=[]
    for i,item in enumerate(reversed(qa[-80:]),1):
        j=item.get('internet_god_judgment') or {}
        verdict = 'Pending Internet God review' if not j else (j.get('verdict') or j.get('decision') or 'Reviewed')
        score = '' if not j else str(j.get('score',''))
        rows.append(f"<tr><td>{esc(item.get('id',''))}</td><td>{esc(short(item.get('question',''),180))}</td><td>{esc(short(item.get('answer',''),220))}</td><td><b>{esc(verdict)}</b><br><span class='muted'>{esc(short(j.get('rationale') or j.get('reason') or '',180))}</span></td><td>{esc(score)}</td><td><button class='ghost' onclick=\"delItem('qa','{esc(item.get('id',''))}')\">Delete</button></td></tr>")
    body = ''.join(rows) or "<tr><td colspan='6' class='muted'>No Q&A saved yet. Ask the Local Jetson Tutor a question to add one.</td></tr>"
    return """
<section class='card' id='reviewSection'>
  <div class='sectionHead'><div><div class='eyebrow'>Offline education</div><h2>Saved Q&A + Internet God review</h2></div><button onclick="cmd('connect_internet')">Connect to Internet + Review Q&A + Enrich KB</button></div>
  <p class='muted'>Every offline answer is saved here. Internet God reviews these later and enriches only the local knowledge base when needed.</p>
  <div class='tablewrap'><table><thead><tr><th>ID</th><th>Question</th><th>Local Jetson Tutor answer</th><th>Internet God judgment</th><th>Score</th><th></th></tr></thead><tbody>""" + body + """</tbody></table></div>
</section>"""

def kb_section(kb):
    rows=[]
    for item in reversed(kb[-80:]):
        snippets = item.get('snippets') or []
        first = ''
        if snippets:
            if isinstance(snippets[0], dict): first = snippets[0].get('text') or snippets[0].get('snippet') or ''
            else: first = str(snippets[0])
        rows.append(f"<tr><td>{esc(item.get('id',''))}</td><td>{esc(short(item.get('query') or item.get('question') or '',180))}</td><td>{esc(short(item.get('missing_knowledge') or item.get('summary') or first,260))}</td><td>{esc(item.get('created_at') or item.get('updated_at') or '')}</td><td><button class='ghost' onclick=\"delItem('kb','{esc(item.get('id',''))}')\">Delete</button></td></tr>")
    body=''.join(rows) or "<tr><td colspan='5' class='muted'>No enriched KB items yet.</td></tr>"
    return """
<section class='card' id='kbSection'>
  <div class='sectionHead'><div><div class='eyebrow'>Local storage</div><h2>Local enriched knowledge base</h2></div></div>
  <p class='muted'>Knowledge-only updates saved locally for future offline answers.</p>
  <div class='tablewrap'><table><thead><tr><th>ID</th><th>Topic / question</th><th>Knowledge added</th><th>Time</th><th></th></tr></thead><tbody>""" + body + """</tbody></table></div>
</section>"""

def render_page():
    s, qa, weak, kb = state(), qa_items(), weak_items(), kb_items()
    user = s.get('partial_transcript') or s.get('last_transcript') or 'Waiting for voice or typed input…'
    proc = status_text(s) if s.get('status') in ('thinking','responding','transcribing') else (s.get('speaking_text') or ('Waiting for a question.' if s.get('status')=='idle' else status_text(s)))
    html_doc = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Self-improving Jetson Tutor</title>
<style>
:root{--bg:#071018;--card:#0e1a25;--card2:#111f2d;--line:#243548;--text:#edf5ff;--muted:#91a3b8;--blue:#5b8cff;--green:#22c55e;--amber:#f59e0b;--red:#ef4444}*{box-sizing:border-box}body{margin:0;background:#071018;color:var(--text);font-family:Inter,ui-sans-serif,system-ui,Segoe UI,sans-serif}.app{max-width:1180px;margin:0 auto;padding:24px}h1{font-size:32px;margin:0 0 6px}h2{font-size:20px;margin:0}.muted{color:var(--muted)}.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px}.pill{display:inline-flex;gap:8px;align-items:center;border:1px solid var(--line);background:#0b1621;border-radius:999px;padding:8px 12px;color:var(--muted)}.dot{width:9px;height:9px;border-radius:99px;background:var(--green)}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;margin:16px 0;box-shadow:0 12px 30px #0004}.hero{display:grid;grid-template-columns:1fr 1fr;gap:14px}.statusBox{background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:14px}.label,.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:6px}.value{font-size:18px;line-height:1.35}.sectionHead{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:10px}button{background:var(--blue);color:white;border:0;border-radius:10px;padding:9px 12px;font-weight:700;cursor:pointer}.ghost{background:#162434;color:#dbeafe;border:1px solid var(--line);padding:7px 9px}.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:12px}table{width:100%;border-collapse:collapse;min-width:780px}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{color:#bfdbfe;font-size:12px;text-transform:uppercase;letter-spacing:.06em;background:#0b1621}textarea{width:100%;min-height:70px;border-radius:12px;border:1px solid var(--line);background:#08131e;color:var(--text);padding:10px}.controls{display:grid;grid-template-columns:1fr auto;gap:10px}@media(max-width:800px){.hero,.controls{grid-template-columns:1fr}.top{display:block}}
</style></head><body data-table-sig='__SIG__'><div class='app'>
<div class='top'><div><h1>Self-improving Jetson Tutor</h1><div class='muted'>Offline-first local tutor with later Internet God knowledge-base enrichment.</div></div><div class='pill'><span class='dot'></span><span id='liveDot'>Live</span></div></div>
<section class='card'><div class='hero' id='hero'><div class='statusBox'><div class='label'>User input</div><div class='value' id='userText'>__USER__</div></div><div class='statusBox'><div class='label'>Local Jetson Tutor status</div><div class='value' id='processText'>__PROC__</div></div><div class='statusBox'><div class='label'>System status</div><div class='value' id='statusText'>__STATUS__</div></div><div class='statusBox'><div class='label'>Counts</div><div class='value'>Q&A: __QA_COUNT__ · KB: __KB_COUNT__</div></div></div></section>
<section class='card'><div class='sectionHead'><div><div class='eyebrow'>Typed test</div><h2>Ask Local Jetson Tutor</h2></div></div><div class='controls'><textarea id='askText' placeholder='Type a test question…'></textarea><button onclick="askTyped()">Ask</button></div></section>
__REVIEW__
__KB__
</div><script>
function setText(id,v,fallback){ const el=document.getElementById(id); if(el) el.textContent=(v&&String(v).trim())?String(v):fallback; }
function statusText(s){ const st=s.status||'unknown'; if(st==='idle') return 'Idle / ready'; if(st==='recording') return 'Recording now'; if(st==='transcribing') return 'Transcribing voice'; if(st==='thinking'||st==='responding') return 'Local Jetson Tutor is thinking'; if(st==='speaking') return 'Speaking final answer'; if(st==='error') return 'Error'; return st; }
function tableSig(h){ const qa=h.qa_review||[], kb=h.kb_items||[]; const last=qa.length?qa[qa.length-1]:{}; return [qa.length,kb.length,last.id||'',last.status||'',last.internet_god_judgment?1:0].join(':'); }
async function refreshTables(sig){ const r=await fetch('/?partial='+Date.now(),{cache:'no-store'}); const html=await r.text(); const doc=new DOMParser().parseFromString(html,'text/html'); for(const id of ['reviewSection','kbSection']){ const fresh=doc.getElementById(id), cur=document.getElementById(id); if(fresh&&cur) cur.innerHTML=fresh.innerHTML; } document.body.setAttribute('data-table-sig', sig||''); }
async function cmd(action){ await fetch('/api/command',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action})}); setTimeout(poll,400); }
async function askTyped(){ const el=document.getElementById('askText'); const text=(el.value||'').trim(); if(!text)return; el.value=''; await fetch('/api/command',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action:'ask',text})}); setTimeout(poll,400); }
async function delItem(kind,id){ if(!confirm('Delete '+kind+' item '+id+'?')) return; await fetch('/api/delete',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({kind:kind,id:id})}); refreshTables(''); }
async function poll(){ try{ const r=await fetch('/health?ts='+Date.now(),{cache:'no-store'}); const h=await r.json(); const s=h.state||{}; const sig=tableSig(h); const bodySig=document.body.getAttribute('data-table-sig')||''; if(bodySig && sig && sig!==bodySig && !(document.activeElement && document.activeElement.matches('input,textarea'))) refreshTables(sig).catch(()=>{}); setText('liveDot','Live','Live'); setText('statusText',statusText(s),'Unknown'); setText('userText',s.partial_transcript||s.last_transcript,'Waiting for voice or typed input…'); const proc=(s.status==='thinking'||s.status==='responding'||s.status==='transcribing')?statusText(s):(s.speaking_text||(s.status==='idle'?'Waiting for a question.':statusText(s))); setText('processText',proc,'Waiting for a question.'); }catch(e){ setText('liveDot','Offline','Offline'); }}
setInterval(poll,1500); poll();
</script></body></html>"""
    return (html_doc.replace('__SIG__', esc(sig(qa,kb))).replace('__USER__', esc(user)).replace('__PROC__', esc(proc)).replace('__STATUS__', esc(status_text(s))).replace('__QA_COUNT__', str(len(qa))).replace('__KB_COUNT__', str(len(kb))).replace('__REVIEW__', review_section(qa)).replace('__KB__', kb_section(kb)))

class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype='text/html'):
        if isinstance(body, str): body = body.encode('utf-8')
        self.send_response(code); self.send_header('content-type', ctype); self.send_header('content-length', str(len(body))); self.send_header('cache-control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health':
            s, qa, weak, kb = state(), qa_items(), weak_items(), kb_items()
            body = {'ok': True, 'mode': 'self-improving-jetson-tutor-simple', 'state': s, 'qa_review': qa, 'weak_answers': weak, 'kb_items': kb, 'qa_count': len(qa), 'kb_count': len(kb)}
            return self.send(200, json.dumps(body, ensure_ascii=False), 'application/json')
        return self.send(200, render_page())
    def do_POST(self):
        length = int(self.headers.get('content-length') or 0)
        try: data = json.loads(self.rfile.read(length) or b'{}')
        except Exception: data = {}
        path = urlparse(self.path).path
        if path == '/api/command':
            action = data.get('action') or 'status'
            if action == 'ask': command('ask', text=data.get('text',''))
            elif action in ('connect_internet','review_weak_answers'): command('connect_internet')
            elif action in ('start','stop','status','say'): command(action, **{k:v for k,v in data.items() if k!='action'})
            else: command(action, **{k:v for k,v in data.items() if k!='action'})
            return self.send(200, json.dumps({'ok': True}), 'application/json')
        if path == '/api/delete':
            kind, ident = data.get('kind'), str(data.get('id') or '')
            if kind == 'qa':
                write_json(QA_FILE, [x for x in qa_items() if str(x.get('id')) != ident])
            elif kind == 'kb':
                write_json(KB_FILE, [x for x in kb_items() if str(x.get('id')) != ident])
            elif kind == 'gap':
                write_json(WEAK_FILE, [x for x in weak_items() if str(x.get('id')) != ident])
            return self.send(200, json.dumps({'ok': True}), 'application/json')
        return self.send(404, json.dumps({'ok': False, 'error': 'not found'}), 'application/json')
    def log_message(self, fmt, *args): pass

if __name__ == '__main__':
    print(f'Jetson Tutor dashboard listening on 127.0.0.1:{PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()

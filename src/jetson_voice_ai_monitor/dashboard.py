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
NONSENSE_FILE = BASE/'nonsense_inputs.json'
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

def esc(x): return html.escape(str(x if x is not None else ''))
def short(x, n=260):
    x = str(x if x is not None else '')
    return x if len(x) <= n else x[:n-1] + '…'

def state(): return read_json(STATE_FILE, {})
def qa_items(): return read_json(QA_FILE, [])
def weak_items(): return read_json(WEAK_FILE, [])
def kb_items(): return read_json(KB_FILE, [])
def nonsense_items(): return read_json(NONSENSE_FILE, [])

def internet_status_from_state(s):
    if bool((s or {}).get('internet_session_active')):
        return {'online': True, 'label': 'Internet God connected for review'}
    return {'online': False, 'label': 'Offline by default'}

def command(action, **kw):
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with COMMANDS_FILE.open('a') as f:
        f.write(json.dumps({'action': action, **kw, 'ts': time.time()}, ensure_ascii=False) + '\n')

def sig(qa, kb, nonsense):
    parts = [str(len(qa)), str(len(kb)), str(len(nonsense))]
    for x in qa[-100:]:
        j = x.get('internet_god_judgment') or {}
        parts.extend([str(x.get('id','')), str(x.get('status','')), str(x.get('reviewed_at','')), str(j.get('score','')), str(j.get('needs_enrichment','')), str(x.get('answer',''))[:80]])
    for x in kb[-100:]:
        parts.extend([str(x.get('id','')), str(x.get('ts','')), str(x.get('query',''))[:80], str(len(x.get('snippets') or []))])
    for x in nonsense[-50:]:
        parts.extend([str(x.get('id','')), str(x.get('ts','')), str(x.get('reason','')), str(x.get('text',''))[:80]])
    return str(abs(hash('|'.join(parts))))

def status_text(s):
    st = s.get('status') or 'unknown'
    if st == 'idle': return 'Idle / ready'
    if st == 'recording': return 'Recording now'
    if st == 'transcribing': return 'Transcribing voice'
    if st in ('thinking','responding'): return 'Local Jetson Tutor is thinking'
    if st == 'speaking': return 'Speaking final answer'
    if st == 'error': return 'Error'
    return st

def top_status_line(s):
    net = internet_status_from_state(s)
    bits = [status_text(s), net.get('label') or 'Offline by default']
    if s.get('last_error'):
        bits.append('Note: ' + str(s.get('last_error'))[:140])
    return ' • '.join(bits)

def score_badge(score):
    try:
        val = float(score)
        label = f'{val:.2f}' if val <= 1 else f'{val:.0f}'
        cls = 'score-good' if val >= 0.75 else ('score-mid' if val >= 0.45 else 'score-low')
        return f"<span class='badge {cls}'>Score {esc(label)}</span>"
    except Exception:
        return "<span class='badge badge-pending'>No score</span>"

def review_status_badge(item):
    if item.get('reviewed_at'):
        return "<span class='badge badge-reviewed'>Reviewed</span>"
    return "<span class='badge badge-pending'><span id='reviewSpin' class='spinner tiny hidden'></span>Pending Internet God</span>"

def review_section(items):
    rows=[]
    for x in list(items)[-80:][::-1]:
        j = x.get('internet_god_judgment') or {}
        need = 'Needs KB update' if j.get('needs_enrichment') else ('Good answer' if x.get('reviewed_at') else 'Waiting')
        rows.append(f"<tr><td>{review_status_badge(x)}<br>{score_badge(j.get('score'))}</td><td><b>{esc(short(x.get('question',''),220))}</b><div class='muted'>{esc(x.get('ts',''))}</div></td><td class='completeAnswer'>{esc(x.get('answer',''))}</td><td>{esc(need)}<br><span class='muted'>{esc(short(j.get('rationale') or j.get('reason') or '',220))}</span></td><td><button class='ghost' onclick=\"delItem('qa','{esc(x.get('id',''))}')\">Delete</button></td></tr>")
    body = ''.join(rows) if rows else "<tr><td colspan='5' class='muted'>No saved Q&A yet. Ask a question to save it for later Internet God review.</td></tr>"
    return """<section class='card' id='reviewSection'>
  <div class='sectionHead'><div><div class='eyebrow'>Offline review queue</div><h2>Saved Q&A + Internet God review</h2></div><button id="connectBtn" onclick="cmd('connect_internet')">Connect to Internet + Review Q&A + Enrich KB</button></div>
  <p class='muted'>Local Jetson Tutor answers first. Later, Internet God reviews saved Q&A and enriches only the local knowledge base when needed.</p>
  <div class='tablewrap'><table><thead><tr><th>Status</th><th>User question</th><th>Complete Local Jetson Tutor answer</th><th>Internet God judgment</th><th></th></tr></thead><tbody>""" + body + """</tbody></table></div>
</section>"""

def kb_section(items):
    rows=[]
    for x in list(items)[-80:][::-1]:
        text = x.get('missing_knowledge') or x.get('suggested_improvement') or 'knowledge only'
        rows.append(f"<tr><td>{esc(x.get('id',''))}</td><td><b>{esc(short(x.get('query') or x.get('question') or '',200))}</b></td><td>{esc(short(text,320))}</td><td>{esc(x.get('ts',''))}</td><td><button class='ghost' onclick=\"delItem('kb','{esc(x.get('id',''))}')\">Delete</button></td></tr>")
    body = ''.join(rows) if rows else "<tr><td colspan='5' class='muted'>No enriched KB items yet.</td></tr>"
    return """<section class='card' id='kbSection'>
  <div class='sectionHead'><div><div class='eyebrow'>Local storage</div><h2>Local enriched knowledge base</h2></div></div>
  <p class='muted'>Knowledge-only updates saved locally for future offline answers.</p>
  <div class='tablewrap'><table><thead><tr><th>ID</th><th>Topic / question</th><th>Knowledge added</th><th>Time</th><th></th></tr></thead><tbody>""" + body + """</tbody></table></div>
</section>"""

def nonsense_html(items):
    rows=[]
    for x in list(items)[-20:][::-1]:
        rows.append(f"<tr><td>{esc(x.get('ts',''))}</td><td>{esc(x.get('reason',''))}</td><td>{esc(short(x.get('text',''),180))}</td><td>{esc(x.get('source',''))}</td></tr>")
    body = ''.join(rows) if rows else "<tr><td colspan='4' class='muted'>No unclear/gibberish inputs have been filtered yet.</td></tr>"
    return """<section class='card' id='nonsenseSection'>
  <div class='sectionHead'><div><div class='eyebrow'>Input safety</div><h2>Filtered unclear inputs</h2></div></div>
  <p class='muted'>These were recorded but not sent to Local Jetson Tutor or Internet God review.</p>
  <div class='tablewrap'><table><thead><tr><th>Time</th><th>Reason</th><th>Input</th><th>Source</th></tr></thead><tbody>""" + body + """</tbody></table></div>
</section>"""

def render_page():
    s, qa, kb, nonsense = state(), qa_items(), kb_items(), nonsense_items()
    net = internet_status_from_state(s)
    busy = s.get('status') in ('recording','transcribing','thinking','responding','speaking') or bool(s.get('speaking'))
    user = s.get('partial_transcript') or s.get('last_transcript') or 'Waiting for voice or typed input…'
    answer = s.get('partial_response') or s.get('last_response') or 'No Local Jetson Tutor answer yet.'
    html_doc = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Self-improving Jetson Tutor</title>
<style>
:root{--bg:#071018;--card:#0e1a25;--card2:#111f2d;--line:#243548;--text:#edf5ff;--muted:#91a3b8;--blue:#5b8cff;--green:#22c55e;--amber:#f59e0b;--red:#ef4444}*{box-sizing:border-box}body{margin:0;background:#071018;color:var(--text);font-family:Inter,ui-sans-serif,system-ui,Segoe UI,sans-serif}.app{max-width:1120px;margin:0 auto;padding:24px}h1{font-size:32px;margin:0 0 6px}h2{font-size:20px;margin:0}.muted{color:var(--muted)}.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:14px}.statusLine{display:flex;align-items:center;gap:10px;border:1px solid var(--line);background:#0b1621;border-radius:14px;padding:10px 13px;color:#dbeafe;min-height:42px}.dot{width:9px;height:9px;border-radius:99px;background:var(--green);flex:0 0 auto}.dot.off{background:var(--red)}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;margin:16px 0;box-shadow:0 12px 30px #0004}.qaHero{display:grid;grid-template-columns:1fr;gap:14px}.qaBox{background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:16px}.qaBox.answer{border-color:#285d41;background:#0d201b}.label,.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:7px}.questionText{font-size:22px;line-height:1.35}.answerText{font-size:24px;line-height:1.36}.completeAnswer{white-space:pre-wrap;min-width:320px;line-height:1.35}.sectionHead{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:10px}button{background:var(--blue);color:white;border:0;border-radius:10px;padding:9px 12px;font-weight:700;cursor:pointer}.badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:800;border:1px solid var(--line);white-space:nowrap}.badge-reviewed{background:#06391f;color:#86efac;border-color:#166534}.badge-pending{background:#2a2108;color:#fde68a;border-color:#92400e}.score-good{background:#052e1a;color:#bbf7d0;border-color:#15803d}.score-mid{background:#2a2108;color:#fde68a;border-color:#a16207}.score-low{background:#3b0a0a;color:#fecaca;border-color:#b91c1c}.spinner{display:inline-block;width:16px;height:16px;border:2px solid #ffffff44;border-top-color:#fff;border-radius:50%;animation:spin .9s linear infinite;vertical-align:-3px}.spinner.tiny{width:12px;height:12px;border-width:2px}@keyframes spin{to{transform:rotate(360deg)}}.hidden{display:none!important}.working{box-shadow:0 0 0 1px #5b8cff55,0 0 28px #5b8cff22}.ghost{background:#162434;color:#dbeafe;border:1px solid var(--line);padding:7px 9px}.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:12px}table{width:100%;border-collapse:collapse;min-width:780px}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{color:#bfdbfe;font-size:12px;text-transform:uppercase;letter-spacing:.06em;background:#0b1621}textarea{width:100%;min-height:70px;border-radius:12px;border:1px solid var(--line);background:#08131e;color:var(--text);padding:10px}.controls{display:grid;grid-template-columns:1fr auto;gap:10px}@media(max-width:800px){.controls{grid-template-columns:1fr}.top{display:block}.answerText{font-size:20px}.questionText{font-size:19px}}
</style></head><body data-table-sig='__SIG__'><div class='app'>
<div class='top'><div><h1>Self-improving Jetson Tutor</h1><div class='muted'>Offline-first local tutor with later Internet God knowledge-base enrichment.</div></div></div>
<div class='statusLine' id='statusLine'><span id='workSpin' class='spinner hidden'></span><span id='statusDot' class='dot'></span><span id='systemStatus'>__STATUS_LINE__</span></div>
<section class='card __BUSY_CLASS__'><div class='qaHero'><div class='qaBox'><div class='label'>User question</div><div class='questionText' id='userQuestion'>__USER__</div></div><div class='qaBox answer'><div class='label'>Local Jetson Tutor answer</div><div class='answerText' id='tutorAnswer'>__ANSWER__</div></div></div></section>
__REVIEW__
__NONSENSE__
__KB__
<section class='card'><div class='sectionHead'><div><div class='eyebrow'>Typed test</div><h2>Ask Local Jetson Tutor</h2></div></div><div class='controls'><textarea id='askText' placeholder='Type a test question…'></textarea><button onclick="askTyped()">Ask</button></div></section>
</div><script>
function setText(id,v,fallback){ const el=document.getElementById(id); if(el) el.textContent=(v&&String(v).trim())?String(v):fallback; }
function statusText(s){ const st=s.status||'unknown'; if(st==='idle') return 'Idle / ready'; if(st==='recording') return 'Recording now'; if(st==='transcribing') return 'Transcribing voice'; if(st==='thinking'||st==='responding') return 'Local Jetson Tutor is thinking'; if(st==='speaking') return 'Speaking final answer'; if(st==='error') return 'Error'; return st; }
function tableSig(h){ if(h.table_sig) return String(h.table_sig); const qa=h.qa_review||[], kb=h.kb_items||[], ni=h.nonsense_inputs||[]; return [qa.length,kb.length,ni.length,JSON.stringify(qa).length,JSON.stringify(kb).length].join(':'); }
let internetConnectingUntil=0;
function showInternetConnecting(){ internetConnectingUntil=Date.now()+12000; setText('systemStatus','Connecting to Internet God… reviewing saved Q&A and preparing KB enrichment.','Connecting to Internet God…'); const spin=document.getElementById('workSpin'); if(spin) spin.classList.remove('hidden'); const review=document.getElementById('reviewSection'); if(review) review.classList.add('working'); document.querySelectorAll('#reviewSpin').forEach(el=>el.classList.remove('hidden')); const btn=document.getElementById('connectBtn'); if(btn){ btn.disabled=true; btn.textContent='Connecting to Internet God…'; } }
function clearInternetConnectingIfDone(s){ if(Date.now()>internetConnectingUntil || (s && s.internet_session_active===false && s.status==='idle')){ internetConnectingUntil=0; const btn=document.getElementById('connectBtn'); if(btn){ btn.disabled=false; btn.textContent='Connect to Internet + Review Q&A + Enrich KB'; } const review=document.getElementById('reviewSection'); if(review) review.classList.remove('working'); } }
function statusLine(h,s){ if(Date.now()<internetConnectingUntil) return 'Connecting to Internet God… reviewing saved Q&A and preparing KB enrichment.'; const bits=[statusText(s), (h.internet&&h.internet.label)||'Offline by default']; if(s.last_error) bits.push('Note: '+String(s.last_error).slice(0,140)); return bits.join(' • '); }
async function refreshTables(sig){ const r=await fetch('/?partial='+Date.now(),{cache:'no-store'}); const html=await r.text(); const doc=new DOMParser().parseFromString(html,'text/html'); for(const id of ['reviewSection','nonsenseSection','kbSection']){ const fresh=doc.getElementById(id), cur=document.getElementById(id); if(fresh&&cur) cur.innerHTML=fresh.innerHTML; } document.body.setAttribute('data-table-sig', sig||''); if(Date.now()<internetConnectingUntil){ const btn=document.getElementById('connectBtn'); if(btn){ btn.disabled=true; btn.textContent='Connecting to Internet God…'; } document.querySelectorAll('#reviewSpin').forEach(el=>el.classList.remove('hidden')); } }
async function cmd(action){ if(action==='connect_internet'||action==='review_weak_answers') showInternetConnecting(); await fetch('/api/command',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action})}); setTimeout(poll,250); }
async function askTyped(){ const el=document.getElementById('askText'); const text=(el.value||'').trim(); if(!text)return; el.value=''; await fetch('/api/command',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action:'ask',text})}); setTimeout(poll,400); }
async function delItem(kind,id){ if(!confirm('Delete '+kind+' item '+id+'?')) return; await fetch('/api/delete',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({kind:kind,id:id})}); refreshTables(''); }
async function poll(){ try{ const r=await fetch('/health?ts='+Date.now(),{cache:'no-store'}); const h=await r.json(); const s=h.state||{}; const ts=tableSig(h); const bodySig=document.body.getAttribute('data-table-sig')||''; if(bodySig && ts && ts!==bodySig && !(document.activeElement && document.activeElement.matches('input,textarea'))) refreshTables(ts).catch(()=>{}); clearInternetConnectingIfDone(s); const busy=(Date.now()<internetConnectingUntil)||['recording','transcribing','thinking','responding','speaking'].includes(s.status)||!!s.speaking; const spin=document.getElementById('workSpin'); if(spin) spin.classList.toggle('hidden',!busy); const dot=document.getElementById('statusDot'); if(dot) dot.classList.toggle('off', s.status==='error'); setText('systemStatus',statusLine(h,s),'Idle / ready • Offline by default'); setText('userQuestion',s.partial_transcript||s.last_transcript,'Waiting for voice or typed input…'); setText('tutorAnswer',s.partial_response||s.last_response,'No Local Jetson Tutor answer yet.'); }catch(e){ setText('systemStatus','Dashboard offline: waiting for local service…','Dashboard offline'); const dot=document.getElementById('statusDot'); if(dot) dot.classList.add('off'); }}
setInterval(poll,1500); poll();
</script></body></html>"""
    return (html_doc.replace('__SIG__', esc(sig(qa,kb,nonsense))).replace('__STATUS_LINE__', esc(top_status_line(s))).replace('__BUSY_CLASS__', 'working' if busy else '').replace('__USER__', esc(user)).replace('__ANSWER__', esc(answer)).replace('__REVIEW__', review_section(qa)).replace('__NONSENSE__', nonsense_html(nonsense)).replace('__KB__', kb_section(kb)))

class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype='text/html'):
        if isinstance(body, str): body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('content-type', ctype)
        self.send_header('content-length', str(len(body)))
        self.send_header('cache-control','no-store')
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health':
            s, qa, weak, kb, nonsense = state(), qa_items(), weak_items(), kb_items(), nonsense_items()
            body = {'ok': True, 'mode': 'self-improving-jetson-tutor-simple-v2', 'state': s, 'qa_review': qa, 'weak_answers': weak, 'kb_items': kb, 'nonsense_inputs': nonsense, 'qa_count': len(qa), 'nonsense_count': len(nonsense), 'kb_count': len(kb), 'table_sig': sig(qa, kb, nonsense), 'internet': internet_status_from_state(s)}
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
            elif action in ('start','stop','say','status'): command(action, **{k:v for k,v in data.items() if k!='action'})
            else: command(action)
            return self.send(200, json.dumps({'ok': True}), 'application/json')
        if path == '/api/delete':
            kind, item_id = data.get('kind'), data.get('id')
            if kind == 'qa': write_json(QA_FILE, [x for x in qa_items() if x.get('id') != item_id])
            elif kind == 'gap': write_json(WEAK_FILE, [x for x in weak_items() if x.get('id') != item_id])
            elif kind == 'kb': write_json(KB_FILE, [x for x in kb_items() if x.get('id') != item_id])
            else: return self.send(400, json.dumps({'ok': False, 'error': 'bad kind'}), 'application/json')
            return self.send(200, json.dumps({'ok': True}), 'application/json')
        return self.send(404, json.dumps({'ok': False}), 'application/json')
    def log_message(self, fmt, *args): return

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()

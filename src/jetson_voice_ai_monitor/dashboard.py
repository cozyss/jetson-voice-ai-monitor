#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, os, urllib.parse, html, time

BASE=os.environ.get('VOICE_AI_BASE','/workspace/voice-ai')
STATE=os.path.join(BASE,'state.json')
EVENTS=os.path.join(BASE,'events.jsonl')
COMMANDS=os.path.join(BASE,'commands.jsonl')
CONVERSATION=os.path.join(BASE,'conversation.json')
WEAK_ANSWERS=os.path.join(BASE,'weak_answers.json')
PORT=int(os.environ.get('VOICE_DASHBOARD_PORT','7862'))

TOOL_CATALOG=[
 {'name':'run_python_code','kind':'local code','description':'Run Python on the Jetson for calculations, parsing, and small automation tasks.','state_key':'tool_calling_enabled'},
 {'name':'run_shell_command','kind':'local shell','description':'Run safe local shell/status commands such as ping, process checks, and hardware status.','state_key':'tool_calling_enabled'},
 {'name':'get_current_weather','kind':'web API','description':'Fetch current weather via Open-Meteo when internet is available.','state_key':'weather_enabled'},
 {'name':'self_improve','kind':'Solid notify','description':'Send implementation requests to the Solid maintainer agent when a capability is missing.','state_key':'self_improve_enabled'},
]

def read_json(path, fallback):
    try:
        with open(path) as f: return json.load(f)
    except Exception as e:
        if path == STATE:
            return {'status':'not-running','last_error':str(e),'mode':'voice-monitor','recording_seconds':0}
        return fallback

def read_state(): return read_json(STATE,{})
def read_weak_answers(): return read_json(WEAK_ANSWERS,[])

def tail_events(n=280):
    try:
        with open(EVENTS) as f: lines=f.readlines()[-n:]
        out=[]
        for line in lines:
            if not line.strip(): continue
            try: out.append(json.loads(line))
            except Exception: pass
        return out
    except Exception: return []

def esc(x): return html.escape('' if x is None else str(x))
def js(x): return json.dumps(x, ensure_ascii=False)
def short(x,n=180):
    x='' if x is None else str(x)
    return x if len(x)<=n else x[:n-1]+'…'
def clean_ts(ts):
    return (str(ts).replace('T',' ').replace('+00:00',' UTC').replace('Z',' UTC') if ts else '')
def pct(x):
    try: return f"{float(x)*100:.0f}%"
    except Exception: return '—'

def voice_label(v):
    if v == 'system': return 'System judge/tools · female voice'
    if v == 'assistant': return 'Qwen/local answer · male voice'
    return 'Not speaking'

def route_label(route):
    if route == 'qwen': return 'Yes — fulfill locally with Qwen/tools'
    if route == 'self_improve': return 'No — needs self-improvement first'
    if route: return route
    return 'No judge decision yet'

def build_tools(state, events):
    counts={}; last={}
    for e in events:
        if e.get('kind')=='tool_call':
            name=e.get('message','') or e.get('name','')
            if name and not str(name).startswith('{'):
                counts[name]=counts.get(name,0)+1; last[name]=e.get('ts','')
    tools=[]
    for t in TOOL_CATALOG:
        tools.append({**t,'enabled':bool(state.get(t['state_key'], True)),'calls_recent':counts.get(t['name'],0),'last_used':last.get(t['name'],'')})
    known={t['name'] for t in TOOL_CATALOG}
    for name,c in sorted(counts.items()):
        if name == 'note_tool_use' and not state.get('force_tool_each_turn', False): continue
        if name not in known:
            tools.append({'name':name,'kind':'observed','description':'Observed in recent event logs.','enabled':True,'calls_recent':c,'last_used':last.get(name,'')})
    return tools

def build_recent_turns(events, state, limit=8):
    turns=[]; cur=None
    for e in events:
        k=e.get('kind'); msg=e.get('message','') or ''
        if k in ('transcript','thinking') and (k=='transcript' or e.get('text') or 'Sending text to Qwen' in msg):
            text=e.get('text') or msg
            if text == 'Sending text to Qwen': text=e.get('request') or text
            cur={'ts':e.get('ts',''),'input':text,'judge':None,'tools':[],'qwen':'','source':e.get('source','voice') if k!='transcript' else 'voice'}
            turns.append(cur)
        elif k=='system_judge':
            if cur is None:
                cur={'ts':e.get('ts',''),'input':'(judge event)','judge':None,'tools':[],'qwen':'','source':'system'}; turns.append(cur)
            cur['judge']={'route':e.get('route',''),'reason':msg,'confidence':e.get('confidence'),'model':e.get('model','')}
        elif k=='tool_call':
            if cur is None:
                cur={'ts':e.get('ts',''),'input':'(tool call)','judge':None,'tools':[],'qwen':'','source':'system'}; turns.append(cur)
            cur['tools'].append({'name':msg,'detail':e.get('request') or e.get('command') or e.get('location') or e.get('reason') or ''})
        elif k=='response':
            if cur is None:
                cur={'ts':e.get('ts',''),'input':'(response)','judge':None,'tools':[],'qwen':msg,'source':'system'}; turns.append(cur)
            else: cur['qwen']=msg
    # Ensure the newest state is visible even if event grouping missed it.
    if not turns and (state.get('last_transcript') or state.get('last_response')):
        turns=[{'ts':state.get('updated_at',''),'input':state.get('last_transcript',''),'judge':state.get('last_system_judge'), 'tools':[], 'qwen':state.get('last_response',''), 'source':'state'}]
    return list(reversed(turns[-limit:]))

def pipeline_html(state):
    judge=state.get('last_system_judge') or {}
    route=judge.get('route','')
    can_local = 'Yes' if route == 'qwen' else ('No' if route == 'self_improve' else 'Unknown')
    improve=judge.get('improvement_request') or ''
    status=state.get('status','unknown')
    user_text=state.get('partial_transcript') or state.get('last_transcript') or ''
    qwen_text=state.get('partial_response') or state.get('last_response') or ''
    judge_audio = judge.get('spoken_status') or ('Silent — request is routed directly to Qwen/local tools.' if route == 'qwen' else 'No system-status speech yet.')
    local_plan = judge.get('local_plan') or (judge.get('reason') if route == 'qwen' else '')
    cards=[
        ('1','User audio transcript','Microphone / Whisper', user_text or 'Waiting for speech…', 'input'),
        ('2','System judge decision','Can this be fulfilled locally?', route_label(route), 'judge'),
        ('3','Judge rationale','Structured routing trace — dashboard only', judge.get('reason') or 'No judge decision yet.', 'judge'),
        ('4','Local/offline plan','How the request will be handled without relying on internet', local_plan or 'No local plan yet.', 'judge' if route == 'qwen' else 'ok'),
        ('5','Judge audio transcript','Spoken only for self-improvement; otherwise silent', judge_audio, 'judge'),
        ('6','Self-improvement need','Concrete request when current system cannot fulfill it', improve or 'None for the current turn.', 'improve' if improve else 'ok'),
        ('7','Qwen transcript','Male local-answer voice output', qwen_text or ('Waiting for Qwen…' if status in ('thinking','responding') else 'No Qwen answer yet.'), 'qwen'),
    ]
    out=''
    for num,title,sub,body,kind in cards:
        out += f"<section class='pipe {kind}'><div class='num'>{num}</div><div class='pipebody'><div class='pipehead'><h3>{esc(title)}</h3><span>{esc(sub)}</span></div><div class='pipetext'>{esc(body)}</div></div></section>"
    return f"<div class='decisionbar'><div><b>Fulfillable locally?</b><span>{can_local}</span></div><div><b>Route</b><span>{esc(route or 'none')}</span></div><div><b>Confidence</b><span>{esc(pct(judge.get('confidence')))}</span></div><div><b>Judge audio</b><span>{'spoken' if judge.get('judge_audio_spoken') else 'silent'}</span></div></div>{out}"

def turns_html(turns):
    if not turns: return "<div class='empty'>No recent requests yet.</div>"
    out=''
    for t in turns:
        j=t.get('judge') or {}
        tools=''.join(f"<span class='chip'>{esc(x.get('name'))}{(': '+esc(short(x.get('detail'),80))) if x.get('detail') else ''}</span>" for x in t.get('tools',[])) or "<span class='muted'>No tools logged</span>"
        out += f"""<article class='turn'>
          <div class='turntop'><b>{esc(t.get('source',''))}</b><span>{esc(clean_ts(t.get('ts','')))}</span></div>
          <div class='turngrid'>
            <div><label>User</label><p>{esc(t.get('input',''))}</p></div>
            <div><label>Judge</label><p><b>{esc(j.get('route',''))}</b>{' · '+esc(short(j.get('reason',''),160)) if j.get('reason') else ''}</p></div>
            <div><label>Tools / self-improve</label><p>{tools}</p></div>
            <div><label>Qwen / spoken final</label><p>{esc(t.get('qwen','')) or '<span class="muted">Pending / none</span>'}</p></div>
          </div></article>"""
    return out

def weak_answers_html(items, state):
    pending=[x for x in (items or []) if x.get('status','pending')=='pending']
    submitted=[x for x in (items or []) if x.get('status')=='submitted']
    lastq=state.get('last_answer_quality') or {}
    review=state.get('last_internet_review') or {}
    rows=''
    for x in reversed(pending[-20:]):
        rows += f"""<tr><td><b>{esc(x.get('id',''))}</b><br><span class='muted'>{esc(clean_ts(x.get('ts','')))}</span></td><td>{esc(x.get('question',''))}</td><td>{esc(short(x.get('answer',''),260))}</td><td>{esc(x.get('score',''))}</td><td>{esc(x.get('reason',''))}</td></tr>"""
    if not rows:
        rows="<tr><td colspan='5'><div class='empty'>No weak answers are currently queued. When Qwen gives a poor/offline-incomplete answer, it will appear here.</div></td></tr>"
    last_quality = f"score={esc(lastq.get('score','—'))}; answered_well={esc(lastq.get('answered_well','—'))}; reason={esc(lastq.get('reason',''))}" if lastq else 'No answer-quality judgment yet.'
    last_review = esc(json.dumps(review, ensure_ascii=False)[:900]) if review else 'No internet review has run yet.'
    return f"""
    <div class='eduhero'><div><b>Connect to Internet Mode</b><span>Demo mode: process saved weak answers into a Solid self-improvement request.</span></div><button onclick="cmd('connect_internet')">Connect to Internet + Review Queue</button></div>
    <div class='decisionbar'><div><b>Pending weak answers</b><span>{len(pending)}</span></div><div><b>Submitted</b><span>{len(submitted)}</span></div><div><b>Quality judge</b><span>{'on' if state.get('answer_quality_enabled') else 'off'}</span></div><div><b>Mode</b><span>{esc(state.get('connectivity_mode','connect_to_internet_demo'))}</span></div></div>
    <p class='hint'><b>Last answer quality:</b> {last_quality}</p>
    <p class='hint'><b>Last internet review:</b> {last_review}</p>
    <div class='scroll'><table><thead><tr><th>ID / time</th><th>Student question</th><th>Qwen answer</th><th>Score</th><th>Why saved</th></tr></thead><tbody>{rows}</tbody></table></div>
    """

def render_page():
    s=read_state(); ev=tail_events(); tools=build_tools(s,ev); turns=build_recent_turns(ev,s); weak=read_weak_answers()
    status=s.get('status','unknown'); status_cls=''.join(ch for ch in str(status).lower() if ch.isalnum()) or 'unknown'
    banner='Recording now' if status=='recording' else ('Idle and listening for Volume Up' if status=='idle' else str(status).replace('_',' ').title())
    tools_rows=''.join(f"<tr><td><code>{esc(t['name'])}</code></td><td>{esc(t['kind'])}</td><td><span class='pill {'on' if t['enabled'] else 'off'}'>{'on' if t['enabled'] else 'off'}</span></td><td>{t['calls_recent']}</td><td>{esc(clean_ts(t['last_used']))}</td><td>{esc(t['description'])}</td></tr>" for t in tools)
    event_lines='\n'.join(f"{clean_ts(e.get('ts',''))} [{e.get('kind','')}] {e.get('message','')}" for e in ev[-80:])
    devices='<br>'.join(esc((d.get('name','')+' '+d.get('path','')).strip()) for d in s.get('event_devices',[])[:8]) or 'No input devices reported.'
    json_state=esc(json.dumps({k:s.get(k) for k in ['status','last_transcript','last_system_judge','last_response','speaking_text','speaking_voice','last_tool_name','last_tool_result','last_answer_quality','weak_answer_count','weak_answer_list','last_internet_review','connectivity_mode','last_error']}, indent=2, ensure_ascii=False))
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Jetson Voice AI Monitor</title>
<style>
:root{{--bg:#081018;--panel:#0f1b28;--panel2:#121f2d;--line:#25364a;--text:#eaf2ff;--muted:#91a4bb;--blue:#4f8cff;--green:#22c55e;--amber:#f59e0b;--red:#ef4444;--purple:#a78bfa}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at top left,#10233a 0,#081018 38%,#060a0f 100%);font-family:Inter,ui-sans-serif,system-ui,Segoe UI,sans-serif;color:var(--text)}}
.app{{max-width:1440px;margin:0 auto;padding:22px}} header{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px}} h1{{font-size:28px;line-height:1.05;margin:0}} .subtitle{{color:var(--muted);margin-top:7px}} .status{{min-width:280px;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:14px;box-shadow:0 14px 40px rgba(0,0,0,.25)}} .status strong{{display:block;font-size:20px;text-transform:capitalize}} .dot{{display:inline-block;width:10px;height:10px;border-radius:99px;background:var(--green);margin-right:8px}} .status.recording .dot{{background:var(--red);animation:pulse 1s infinite}} .status.thinking .dot,.status.transcribing .dot{{background:var(--amber)}} @keyframes pulse{{50%{{opacity:.35}}}}
.grid{{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(360px,.65fr);gap:16px}} @media(max-width:980px){{.grid,header{{grid-template-columns:1fr;display:block}} .status{{margin-top:12px}}}}
.card{{background:rgba(15,27,40,.88);border:1px solid var(--line);border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 10px 28px rgba(0,0,0,.22)}} .card h2{{font-size:17px;margin:0 0 12px;display:flex;align-items:center;gap:8px}} .muted,.hint{{color:var(--muted)}} .hint{{font-size:13px}} 
.decisionbar{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}} .decisionbar div{{background:#0a1320;border:1px solid #203047;border-radius:14px;padding:11px}} .decisionbar b{{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}} .decisionbar span{{font-size:15px}}
.pipe{{display:grid;grid-template-columns:42px 1fr;gap:12px;border:1px solid var(--line);border-radius:16px;padding:12px;margin:10px 0;background:var(--panel2)}} .pipe .num{{width:42px;height:42px;border-radius:14px;background:#18283a;display:flex;align-items:center;justify-content:center;font-weight:800;color:#cfe1ff}} .pipehead{{display:flex;justify-content:space-between;gap:10px}} .pipe h3{{margin:0;font-size:15px}} .pipehead span{{color:var(--muted);font-size:12px}} .pipetext{{white-space:pre-wrap;margin-top:8px;line-height:1.45}} .pipe.input .num{{background:#1e3a8a}} .pipe.judge .num{{background:#6d28d9}} .pipe.improve .num{{background:#92400e}} .pipe.ok .num{{background:#14532d}} .pipe.qwen .num{{background:#166534}}
.eduhero{{display:flex;justify-content:space-between;gap:12px;align-items:center;background:#0a1320;border:1px solid #35517a;border-radius:16px;padding:14px;margin-bottom:12px}} .eduhero b{{display:block;font-size:18px}} .eduhero span{{display:block;color:var(--muted);font-size:13px;margin-top:4px}}
.controls{{display:grid;grid-template-columns:1fr auto;gap:10px}} input{{width:100%;background:#07111c;border:1px solid #2b3d52;border-radius:12px;padding:12px;color:var(--text)}} button{{background:var(--blue);color:white;border:0;border-radius:12px;padding:11px 14px;font-weight:650;cursor:pointer}} button.secondary{{background:#24364a}} button.stop{{background:var(--red)}} .row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}}
.voicegrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .voice{{padding:12px;border:1px solid #334155;border-radius:14px;background:#0a1320}} .voice b{{display:block}} .voice span{{display:block;color:var(--muted);font-size:13px;margin-top:4px}}
.turn{{border:1px solid var(--line);border-radius:15px;background:#0a1320;margin:10px 0;padding:12px}} .turntop{{display:flex;justify-content:space-between;color:var(--muted);font-size:12px}} .turngrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}} @media(max-width:800px){{.turngrid{{grid-template-columns:1fr}}}} label{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}} p{{margin:4px 0 0;white-space:pre-wrap}} .chip{{display:inline-block;padding:4px 8px;border-radius:999px;border:1px solid #334155;background:#17263a;margin:2px;font-size:12px}}
table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #26374b;padding:8px}} th{{color:#cbd8ea;background:#0a1320;position:sticky;top:0}} code{{color:#9ec5ff}} .pill{{border-radius:999px;padding:2px 7px;font-size:12px;background:#1f2937}} .pill.on{{background:#14532d;color:#bbf7d0}} .pill.off{{background:#4c1d1d;color:#fecaca}} .scroll{{max-height:430px;overflow:auto}} pre{{white-space:pre-wrap;background:#07111c;border:1px solid #203047;border-radius:12px;padding:12px;max-height:330px;overflow:auto;color:#c7d2e2}} .empty{{color:var(--muted);padding:20px;text-align:center;border:1px dashed #334155;border-radius:14px}}
.tabs{{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}} .tab{{background:#17263a}} .tab.active{{background:var(--blue)}} .tabpane{{display:none}} .tabpane.active{{display:block}}
</style></head><body><div class='app'><header><div><h1>Jetson Voice AI Monitor</h1><div class='subtitle'>Clear view of the audio transcript, system judge routing, self-improvement path, local tools, and Qwen answer.</div></div><div class='status {esc(status_cls)}'><strong><span class='dot'></span>{esc(banner)}</strong><div class='hint'>Updated {esc(clean_ts(s.get('updated_at','')))} · Speaking: {esc(voice_label(s.get('speaking_voice')))}</div></div></header>
<div class='grid'><main>
 <section class='card'><h2>🧭 Live decision pipeline</h2>{pipeline_html(s)}</section>
 <section class='card'><h2>🎓 Offline education improvement queue</h2>{weak_answers_html(weak,s)}</section>
 <section class='card'><h2>🎛️ Interactive controls</h2><div class='controls'><input id='askText' placeholder='Type a request to send through the same judge → tool/Qwen pipeline…'><button onclick='ask()'>Ask</button></div><div class='row'><button onclick="cmd('start')">Start recording</button><button class='stop' onclick="cmd('stop')">Stop + transcribe</button><button class='secondary' onclick="cmd('status')">Speak status</button><button class='secondary' onclick="cmd('connect_internet')">Connect Internet</button><button class='secondary' onclick='location.reload()'>Refresh</button></div></section>
 <section class='card'><h2>🧾 Recent audio and answer transcripts</h2>{turns_html(turns)}</section>
</main><aside>
 <section class='card'><h2>🔊 Voices</h2><div class='voicegrid'><div class='voice'><b>System judge / tools</b><span>Female Piper voice. Short routing and tool-status transcript.</span></div><div class='voice'><b>Qwen local answer</b><span>Male Piper voice. Final answer transcript.</span></div></div><p class='hint'>Speaking now: {esc(s.get('speaking_text') or 'not speaking')}</p></section>
 <section class='card'><h2>🧰 Available Qwen agent tools</h2><div class='scroll'><table><thead><tr><th>Tool</th><th>Kind</th><th>State</th><th>Recent</th><th>Description</th></tr></thead><tbody>{tools_rows}</tbody></table></div></section>
 <section class='card'><div class='tabs'><button class='tab active' data-tab='events' onclick='tab(event)'>Events</button><button class='tab' data-tab='devices' onclick='tab(event)'>Devices</button><button class='tab' data-tab='state' onclick='tab(event)'>State JSON</button></div><div id='events' class='tabpane active'><pre>{esc(event_lines)}</pre></div><div id='devices' class='tabpane'><p class='hint'>{devices}</p></div><div id='state' class='tabpane'><pre>{json_state}</pre></div></section>
</aside></div></div><script>
async function send(payload){{await fetch('/api/command',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(payload)}});setTimeout(()=>location.reload(),500)}}
function cmd(action){{send({{action}})}}
function ask(){{const el=document.getElementById('askText'); const text=el.value.trim(); if(!text) return; send({{action:'ask', text}}); el.value='';}}
function tab(ev){{const name=ev.target.dataset.tab; document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===ev.target)); document.querySelectorAll('.tabpane').forEach(x=>x.classList.toggle('active',x.id===name));}}
let lastSig = null;
let lastReloadAt = 0;
function focusedEditing(){{
  const el = document.activeElement;
  return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
}}
async function pollAndRefresh(){{
  try{{
    const r = await fetch('/health?ts='+Date.now(), {{cache:'no-store'}});
    if(!r.ok) return;
    const h = await r.json();
    const s = h.state || h;
    const j = s.last_system_judge || {{}};
    const sig = JSON.stringify([
      s.status, s.partial_transcript, s.last_transcript, s.partial_response, s.last_response,
      s.speaking, s.speaking_text, s.last_tool_name, s.last_error, s.weak_answer_count, JSON.stringify(s.last_answer_quality||{{}}), JSON.stringify(s.last_internet_review||{{}}),
      j.route, j.reason, j.improvement_request, j.judge_audio_spoken
    ]);
    if(lastSig === null){{ lastSig = sig; return; }}
    if(sig !== lastSig && !focusedEditing() && Date.now() - lastReloadAt > 1500){{
      lastReloadAt = Date.now();
      location.reload();
    }}
    lastSig = sig;
    const dot=document.getElementById('liveDot'); if(dot) dot.textContent='Live '+new Date().toLocaleTimeString();
  }}catch(e){{ const dot=document.getElementById('liveDot'); if(dot) dot.textContent='Reconnect…'; }}
}}
setInterval(pollAndRefresh, 1500);
pollAndRefresh();
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): return
    def send_body(self, code, body, ctype='application/json'):
        if not isinstance(body,(bytes,bytearray)):
            body=(body if isinstance(body,str) else json.dumps(body,ensure_ascii=False)).encode()
        self.send_response(code)
        self.send_header('content-type',ctype)
        self.send_header('cache-control','no-store, max-age=0')
        self.send_header('content-length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p=urllib.parse.urlparse(self.path).path
        if p in ('/','/live'):
            self.send_body(200,render_page(),'text/html; charset=utf-8')
        elif p in ('/health','/api/status'):
            s=read_state(); ev=tail_events()
            self.send_body(200,{'ok':True,'mode':'voice-ai-monitor-pipeline-redesign','state':s,'events':ev,'tools':build_tools(s,ev),'interactions':build_recent_turns(ev,s,8),'weak_answers':read_weak_answers()})
        else:
            self.send_body(404,{'error':'not found'})
    def do_POST(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/api/command':
            n=int(self.headers.get('content-length','0') or 0)
            try: data=json.loads(self.rfile.read(n) or b'{}')
            except Exception: data={'action':'status'}
            action=data.get('action') or 'status'
            obj={'action':action}
            if action=='ask': obj['text']=data.get('text','')
            if action=='say': obj['text']=data.get('text',''); obj['voice']=data.get('voice','assistant')
            with open(COMMANDS,'a') as f: f.write(json.dumps(obj,ensure_ascii=False)+'\n')
            self.send_body(200,{'ok':True,'queued':obj})
        else:
            self.send_body(404,{'error':'not found'})

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Jetson Voice AI dashboard on http://0.0.0.0:{PORT}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()

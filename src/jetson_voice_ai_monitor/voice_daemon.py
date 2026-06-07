#!/usr/bin/env python3
import os, sys, time, json, struct, select, subprocess, threading, signal, glob, urllib.request, urllib.error, urllib.parse, queue, re, uuid
from datetime import datetime, timezone
import tempfile

BASE = os.environ.get('VOICE_AI_BASE', '/workspace/voice-ai')
SELF_IMPROVE_ENV = os.path.join(BASE, 'self-improve.env')
try:
    with open(SELF_IMPROVE_ENV) as _envf:
        for _line in _envf:
            _line = _line.strip()
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass
except Exception:
    pass
SYSTEM_JUDGE_ENV = os.path.join(BASE, 'system-judge.env')
try:
    with open(SYSTEM_JUDGE_ENV) as _envf:
        for _line in _envf:
            _line = _line.strip()
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass
except Exception:
    pass
STATE = os.path.join(BASE, 'state.json')
EVENTS = os.path.join(BASE, 'events.jsonl')
COMMANDS = os.path.join(BASE, 'commands.jsonl')
HISTORY = os.path.join(BASE, 'conversation.json')
AUDIO_DIR = os.path.join(BASE, 'recordings')
WHISPER = os.environ.get('VOICE_WHISPER_BIN', '/workspace/whisper.cpp/build/bin/whisper-cli')
WHISPER_MODEL = os.environ.get('VOICE_WHISPER_MODEL', '/workspace/models/whisper/ggml-base.en.bin')
QWEN_URL = os.environ.get('VOICE_QWEN_URL', 'http://127.0.0.1:8083/v1/chat/completions')
ARECORD_DEVICE = os.environ.get('VOICE_ARECORD_DEVICE', 'plughw:0,0')
MAX_RECORD_SECONDS = int(os.environ.get('VOICE_MAX_RECORD_SECONDS', '120'))
QWEN_MAX_TOKENS = int(os.environ.get('VOICE_QWEN_MAX_TOKENS', '1024'))
TTS_ENABLED = os.environ.get('VOICE_TTS_ENABLED', '1') != '0'
TTS_CMD = os.environ.get('VOICE_TTS_CMD', 'piper-lessac-high')
PIPER_BIN = os.environ.get('VOICE_PIPER_BIN', '/workspace/piper/piper/piper')
PIPER_MODEL = os.environ.get('VOICE_PIPER_MODEL', '/workspace/models/piper/en_US-ryan-high.onnx')
PIPER_LENGTH_SCALE = os.environ.get('VOICE_PIPER_LENGTH_SCALE', '0.95')
PIPER_NOISE_SCALE = os.environ.get('VOICE_PIPER_NOISE_SCALE', '0.50')
PIPER_NOISE_W = os.environ.get('VOICE_PIPER_NOISE_W', '0.60')
TTS_AUDIO_DEVICE = os.environ.get('VOICE_TTS_AUDIO_DEVICE', 'plughw:0,0')
SYSTEM_TTS_CMD = os.environ.get('VOICE_SYSTEM_TTS_CMD', 'espeak-robot')
SYSTEM_ESPEAK_VOICE = os.environ.get('VOICE_SYSTEM_ESPEAK_VOICE', 'en+m3')
SYSTEM_ESPEAK_SPEED = os.environ.get('VOICE_SYSTEM_ESPEAK_SPEED', '135')
SYSTEM_ESPEAK_PITCH = os.environ.get('VOICE_SYSTEM_ESPEAK_PITCH', '25')
SYSTEM_PIPER_MODEL = os.environ.get('VOICE_SYSTEM_PIPER_MODEL', '/workspace/models/piper/en_US-lessac-high.onnx')
SYSTEM_PIPER_LENGTH_SCALE = os.environ.get('VOICE_SYSTEM_PIPER_LENGTH_SCALE', '0.88')
SYSTEM_PIPER_NOISE_SCALE = os.environ.get('VOICE_SYSTEM_PIPER_NOISE_SCALE', '0.50')
SYSTEM_PIPER_NOISE_W = os.environ.get('VOICE_SYSTEM_PIPER_NOISE_W', '0.60')
LIVE_TRANSCRIBE_ENABLED = os.environ.get('VOICE_LIVE_TRANSCRIBE_ENABLED', '1') != '0'
LIVE_TRANSCRIBE_INTERVAL = float(os.environ.get('VOICE_LIVE_TRANSCRIBE_INTERVAL', '6'))
USE_PARTIAL_ON_STOP = os.environ.get('VOICE_USE_PARTIAL_ON_STOP', '0') != '0'
TOOL_CALLING_ENABLED = os.environ.get('VOICE_TOOL_CALLING_ENABLED', '1') != '0'
PYTHON_TOOL_TIMEOUT = int(os.environ.get('VOICE_PYTHON_TOOL_TIMEOUT', '20'))
PYTHON_TOOL_MAX_CHARS = int(os.environ.get('VOICE_PYTHON_TOOL_MAX_CHARS', '4000'))
PYTHON_TOOL_WORKDIR = os.environ.get('VOICE_PYTHON_TOOL_WORKDIR', os.path.join(BASE, 'python-tool-workdir'))
SHELL_TOOL_TIMEOUT = int(os.environ.get('VOICE_SHELL_TOOL_TIMEOUT', '30'))
SHELL_TOOL_MAX_CHARS = int(os.environ.get('VOICE_SHELL_TOOL_MAX_CHARS', '2000'))
SHELL_TOOL_WORKDIR = os.environ.get('VOICE_SHELL_TOOL_WORKDIR', BASE)
SELF_IMPROVE_ENABLED = os.environ.get('VOICE_SELF_IMPROVE_ENABLED', '1') != '0'
SELF_IMPROVE_AGENT_ID = os.environ.get('VOICE_SELF_IMPROVE_AGENT_ID', '')
SELF_IMPROVE_API_KEY = os.environ.get('VOICE_SELF_IMPROVE_API_KEY', '')
SELF_IMPROVE_API_URL = os.environ.get('VOICE_SELF_IMPROVE_API_URL', 'https://staging.sld.dev/api/functions/workspace.agent.notify')
SELF_IMPROVE_MAX_CHARS = int(os.environ.get('VOICE_SELF_IMPROVE_MAX_CHARS', '2000'))
HISTORY_TURNS = int(os.environ.get('VOICE_HISTORY_TURNS', '6'))
HISTORY_MAX_CHARS = int(os.environ.get('VOICE_HISTORY_MAX_CHARS', '6000'))
HISTORY_ENABLED = os.environ.get('VOICE_HISTORY_ENABLED', '1') != '0'
FORCE_TOOL_EACH_TURN = os.environ.get('VOICE_FORCE_TOOL_EACH_TURN', '0') != '0'
SYSTEM_JUDGE_ENABLED = os.environ.get('VOICE_SYSTEM_JUDGE_ENABLED', '0') != '0'
SYSTEM_JUDGE_MODEL = os.environ.get('VOICE_SYSTEM_JUDGE_MODEL', 'openai/gpt-4o-mini')
SYSTEM_JUDGE_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
SYSTEM_JUDGE_URL = os.environ.get('VOICE_SYSTEM_JUDGE_URL', 'https://openrouter.ai/api/v1/chat/completions')
SYSTEM_JUDGE_TIMEOUT = float(os.environ.get('VOICE_SYSTEM_JUDGE_TIMEOUT', '8'))
SYSTEM_JUDGE_TTS = os.environ.get('VOICE_SYSTEM_JUDGE_TTS', '1') != '0'
SYSTEM_JUDGE_MAX_CHARS = int(os.environ.get('VOICE_SYSTEM_JUDGE_MAX_CHARS', '1200'))
SYSTEM_JUDGE_SPEAK_ALLOW = os.environ.get('VOICE_SYSTEM_JUDGE_SPEAK_ALLOW', 'System check: I can handle that locally.')
SYSTEM_JUDGE_SPEAK_IMPROVE = os.environ.get('VOICE_SYSTEM_JUDGE_SPEAK_IMPROVE', 'System check: I cannot fully handle that yet. Sending an improvement request.')
SYSTEM_JUDGE_REQUIRE_INTERNET = os.environ.get('VOICE_SYSTEM_JUDGE_REQUIRE_INTERNET', '1') != '0'
SYSTEM_JUDGE_NET_PROBE_URL = os.environ.get('VOICE_SYSTEM_JUDGE_NET_PROBE_URL', 'https://openrouter.ai/api/v1/models')
SYSTEM_JUDGE_NET_PROBE_TIMEOUT = float(os.environ.get('VOICE_SYSTEM_JUDGE_NET_PROBE_TIMEOUT', '1.5'))
SYSTEM_JUDGE_NET_CACHE_SECONDS = float(os.environ.get('VOICE_SYSTEM_JUDGE_NET_CACHE_SECONDS', '30'))
SYSTEM_JUDGE_SELF_IMPROVE_MIN_CONFIDENCE = float(os.environ.get('VOICE_SYSTEM_JUDGE_SELF_IMPROVE_MIN_CONFIDENCE', '0.88'))
_system_judge_net_cache = {'ts': 0.0, 'ok': False}

# Offline education knowledge-base loop: Qwen answers locally, then grades whether
# the answer was actually useful. Weak/missing-knowledge answers are stored until
# internet is available, then used ONLY to enrich the local knowledge base.
WEAK_ANSWERS = os.path.join(BASE, 'weak_answers.json')
QA_REVIEW_LOG = os.path.join(BASE, 'qa_review_queue.json')
NONSENSE_INPUT_LOG = os.path.join(BASE, 'nonsense_inputs.json')
NONSENSE_INPUT_MAX_ITEMS = int(os.environ.get('VOICE_NONSENSE_INPUT_MAX_ITEMS', '200'))
INPUT_FILTER_ENABLED = os.environ.get('VOICE_INPUT_FILTER_ENABLED', '1') != '0'
QA_REVIEW_MAX_ITEMS = int(os.environ.get('VOICE_QA_REVIEW_MAX_ITEMS', '200'))
KB_DIR = os.path.join(BASE, 'knowledge_base')
KB_FILE = os.path.join(KB_DIR, 'kb_items.json')
KB_ENABLED = os.environ.get('VOICE_KB_ENABLED', '1') != '0'
KB_MAX_CONTEXT_CHARS = int(os.environ.get('VOICE_KB_MAX_CONTEXT_CHARS', '2400'))
KB_FETCH_TIMEOUT = float(os.environ.get('VOICE_KB_FETCH_TIMEOUT', '12'))
ANSWER_QUALITY_ENABLED = os.environ.get('VOICE_ANSWER_QUALITY_ENABLED', '1') != '0'
ANSWER_QUALITY_THRESHOLD = float(os.environ.get('VOICE_ANSWER_QUALITY_THRESHOLD', '0.72'))
WEAK_ANSWER_MAX_ITEMS = int(os.environ.get('VOICE_WEAK_ANSWER_MAX_ITEMS', '200'))
CONNECTIVITY_MODE = os.environ.get('VOICE_CONNECTIVITY_MODE', 'connect_to_internet_demo')

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(KB_DIR, exist_ok=True)
lock = threading.RLock()
record_proc = None
record_path = None
record_started = None
record_session = 0
state = {
    'status': 'starting',
    'mode': 'volume-key-press-to-talk',
    'instructions': 'Volume Up starts recording; Volume Down stops, transcribes, and sends to Qwen.',
    'stt': 'whisper.cpp base.en CPU',
    'llm': 'Qwen3.5-9B-Q4_K_M via FA llama-server',
    'arecord_device': ARECORD_DEVICE,
    'last_transcript': '',
    'partial_transcript': '',
    'last_response': '',
    'partial_response': '',
    'last_error': '',
    'recording_seconds': 0,
    'audio_file': '',
    'tts_enabled': TTS_ENABLED,
        'tts_cmd': TTS_CMD,
        'tts_voice': 'Local Jetson Tutor: male Piper en_US-ryan-high',
        'tts_system_voice': 'Internet God / tools: nice female Piper en_US-lessac-high',
    'live_transcribe_enabled': LIVE_TRANSCRIBE_ENABLED,
    'speaking': False,
    'speaking_text': '',
    'max_output_tokens': QWEN_MAX_TOKENS,
        'tool_calling_enabled': TOOL_CALLING_ENABLED,
    'force_tool_each_turn': FORCE_TOOL_EACH_TURN,
    'system_judge_enabled': SYSTEM_JUDGE_ENABLED,
    'system_judge_model': SYSTEM_JUDGE_MODEL,
    'system_judge_require_internet': SYSTEM_JUDGE_REQUIRE_INTERNET,
    'weather_enabled': True,
    'last_system_judge': {},
    'answer_quality_enabled': False,
    'last_answer_quality': {'enabled': False, 'source': 'internet_god_deferred', 'reason': 'Local tutor does not judge its own answers; Internet God reviews saved Q&A on connect.'},
    'qa_review_count': 0,
    'qa_review_list': [],
    'input_filter_enabled': INPUT_FILTER_ENABLED,
    'nonsense_input_count': 0,
    'nonsense_input_list': [],
    'last_input_filter': {},
    'weak_answer_count': 0,
    'weak_answer_list': [],
    'connectivity_mode': CONNECTIVITY_MODE,
    'last_internet_review': {},
    'internet_session_active': False,
    'internet_status_label': 'Internet unavailable / offline by default',
    'kb_enabled': KB_ENABLED,
    'kb_item_count': 0,
    'kb_last_enrichment': {},
    'self_improve_enabled': SELF_IMPROVE_ENABLED,
    'conversation_memory_enabled': HISTORY_ENABLED,
    'history_turns': HISTORY_TURNS,
    'history_messages': 0,
        'last_tool_name': '',
        'last_tool_result': '',
    'updated_at': '',
    'event_devices': [],
}

def now(): return datetime.now(timezone.utc).isoformat()

def save_state():
    state['updated_at'] = now()
    tmp = f"{STATE}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, 'w') as f: json.dump(state, f, indent=2)
    os.replace(tmp, STATE)

def log_event(kind, message, **extra):
    rec = {'ts': now(), 'kind': kind, 'message': message}
    rec.update(extra)
    with open(EVENTS, 'a') as f: f.write(json.dumps(rec) + '\n')
    with lock:
        state['last_event'] = rec
        save_state()

def set_status(status, **kw):
    with lock:
        state['status'] = status
        state.update(kw)
        save_state()

def load_history():
    if not HISTORY_ENABLED:
        return []
    try:
        with open(HISTORY) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and isinstance(m.get('content'), str)]
    except FileNotFoundError:
        return []
    except Exception as e:
        log_event('history_error', f'Could not load conversation history: {e}')
    return []

def trim_history(messages):
    clean = []
    for m in messages:
        role = m.get('role')
        content = (m.get('content') or '').strip()
        if role not in ('user', 'assistant') or not content:
            continue
        if len(content) > 1200:
            content = content[:1200] + '...'
        clean.append({'role': role, 'content': content})
    clean = clean[-max(0, HISTORY_TURNS * 2):]
    total = 0
    out = []
    for m in reversed(clean):
        c = len(m.get('content',''))
        if out and total + c > HISTORY_MAX_CHARS:
            break
        total += c
        out.append(m)
    return list(reversed(out))

def save_history(messages):
    if not HISTORY_ENABLED:
        return
    trimmed = trim_history(messages)
    tmp = f"{HISTORY}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, 'w') as f:
        json.dump(trimmed, f, indent=2)
    os.replace(tmp, HISTORY)
    with lock:
        state['history_messages'] = len(trimmed)
        state['conversation_memory_enabled'] = HISTORY_ENABLED
        state['history_turns'] = HISTORY_TURNS
        save_state()

def append_history_turn(user_text, assistant_text):
    if not HISTORY_ENABLED:
        return
    user_text = (user_text or '').strip()
    assistant_text = (assistant_text or '').strip()
    if not user_text or not assistant_text:
        return
    hist = load_history()
    hist.append({'role': 'user', 'content': user_text})
    hist.append({'role': 'assistant', 'content': assistant_text})
    save_history(hist)
    log_event('history', f'Conversation memory saved: {len(trim_history(hist))} messages')

def discover_event_devices():
    devices = []
    cur = {}
    try:
        txt = open('/proc/bus/input/devices').read().splitlines()
    except Exception as e:
        log_event('error', f'Cannot read input devices: {e}')
        return []
    for line in txt + ['']:
        if not line.strip():
            if cur.get('handlers'):
                name = cur.get('name','')
                handlers = cur.get('handlers','')
                for h in handlers.split():
                    if h.startswith('event'):
                        # Listen to all kbd/consumer devices; filter key codes later.
                        if ('kbd' in handlers) or ('Consumer Control' in name) or ('EMEET' in name) or ('Logitech' in name):
                            devices.append({'path': '/dev/input/' + h, 'name': name, 'handlers': handlers})
            cur = {}
            continue
        if line.startswith('N: Name='):
            cur['name'] = line.split('=',1)[1].strip().strip('"')
        elif line.startswith('H: Handlers='):
            cur['handlers'] = line.split('=',1)[1].strip()
    # Deduplicate by path.
    seen, out = set(), []
    for d in devices:
        if d['path'] not in seen and os.path.exists(d['path']):
            seen.add(d['path']); out.append(d)
    return out

def recover_stale_recording_locked(reason='recorder process is not active', source='internal'):
    # Caller must hold lock. Used when UI/state says recording but arecord has died or disappeared.
    global record_proc, record_path, record_started
    old_path = record_path or state.get('audio_file', '')
    record_proc = None
    record_path = None
    record_started = None
    state['status'] = 'idle'
    state['recording_seconds'] = 0
    state['last_error'] = ''
    state['partial_transcript'] = ''
    save_state()
    log_event('recording_recovered', f'Stale recording state cleared: {reason}', source=source, audio_file=old_path)
    return old_path

def start_recording(source='key'):
    global record_proc, record_path, record_started, record_session
    with lock:
        if record_proc and record_proc.poll() is None:
            log_event('ignored', 'Start ignored: already recording', source=source)
            return
        if state.get('status') == 'recording':
            recover_stale_recording_locked('start requested but no active recorder exists', source=source)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        record_path = os.path.join(AUDIO_DIR, f'utterance-{ts}.wav')
        record_started = time.time()
        record_session += 1
        session_id = record_session
        state['last_transcript'] = ''
        state['partial_transcript'] = ''
        state['last_response'] = ''
        state['partial_response'] = ''
        state['last_error'] = ''
        state['audio_file'] = record_path
        state['recording_seconds'] = 0
        state['max_output_tokens'] = QWEN_MAX_TOKENS
        save_state()
        cmd = ['arecord', '-D', ARECORD_DEVICE, '-f', 'S16_LE', '-c1', '-r16000', '-t', 'wav', record_path]
        record_proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=open(os.path.join(BASE,'arecord.err'),'ab'), start_new_session=True)
        time.sleep(0.15)
        if record_proc.poll() is not None:
            code = record_proc.returncode
            recover_stale_recording_locked(f'arecord exited immediately with code {code}', source=source)
            return
    if LIVE_TRANSCRIBE_ENABLED:
        threading.Thread(target=live_transcribe_loop, args=(session_id, record_path), daemon=True).start()
    set_status('recording')
    log_event('recording_start', 'Recording started', source=source, audio_file=record_path)

def stop_recording(source='key'):
    global record_proc, record_path, record_started
    with lock:
        proc, path, started = record_proc, record_path, record_started
        if not proc or proc.poll() is not None:
            if state.get('status') == 'recording':
                recover_stale_recording_locked('stop requested but recorder process is gone', source=source)
            else:
                log_event('ignored', 'Stop ignored: not recording', source=source)
            return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception: proc.kill()
    dur = max(0.0, time.time() - (started or time.time()))
    with lock:
        record_proc = None; record_started = None
        state['recording_seconds'] = round(dur, 1)
        save_state()
    log_event('recording_stop', 'Recording stopped', source=source, duration=round(dur,1), audio_file=path)
    threading.Thread(target=process_audio, args=(path,), daemon=True).start()


tts_queue = queue.Queue()

def clean_for_speech(text):
    text = re.sub(r'[`*_#>\[\]{}]', '', text or '')
    text = re.sub(r'https?://\S+', ' link ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tts_say(text, voice='assistant'):
    if not TTS_ENABLED:
        return
    text = clean_for_speech(text)
    if not text:
        return
    voice = voice or 'assistant'
    try:
        fd, wav = tempfile.mkstemp(prefix=f'voice-{voice}-', suffix='.wav', dir='/tmp')
        os.close(fd)
        if voice == 'system':
            # Internet God/tool-status voice: nice female Piper, distinct from the male Local Jetson Tutor answer voice.
            try:
                piper = PIPER_BIN if os.path.exists(PIPER_BIN) else '/workspace/piper/piper'
                subprocess.run([
                    piper,
                    '--model', SYSTEM_PIPER_MODEL,
                    '--length_scale', str(SYSTEM_PIPER_LENGTH_SCALE),
                    '--noise_scale', str(SYSTEM_PIPER_NOISE_SCALE),
                    '--noise_w', str(SYSTEM_PIPER_NOISE_W),
                    '--output_file', wav,
                ], input=text[:500], text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45, check=True)
            except Exception:
                subprocess.run(['espeak-ng', '-v', 'en+f3', '-s', '150', '-p', '55', '-w', wav, text[:500]],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=True)
            subprocess.run(['aplay', '-D', TTS_AUDIO_DEVICE, wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False)
        else:
            # Local Jetson Tutor assistant voice: male Piper en_US-ryan-high.
            piper = PIPER_BIN if os.path.exists(PIPER_BIN) else '/workspace/piper/piper'
            subprocess.run([
                piper,
                '--model', PIPER_MODEL,
                '--length_scale', str(PIPER_LENGTH_SCALE),
                '--noise_scale', str(PIPER_NOISE_SCALE),
                '--noise_w', str(PIPER_NOISE_W),
                '--output_file', wav,
            ], input=text[:800], text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45, check=True)
            subprocess.run(['aplay', '-D', TTS_AUDIO_DEVICE, wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False)
        try: os.unlink(wav)
        except Exception: pass
    except Exception as e:
        log_event('tts_error', str(e), tts_cmd=TTS_CMD, voice=voice)

def tts_worker():
    while True:
        item = tts_queue.get()
        if item is None:
            continue
        if isinstance(item, dict):
            text = item.get('text') or ''
            voice = item.get('voice') or 'assistant'
        else:
            text = item
            voice = 'assistant'
        with lock:
            state['speaking'] = True
            state['speaking_text'] = clean_for_speech(text)[:300]
            state['speaking_voice'] = voice
            save_state()
        log_event('speaking', clean_for_speech(text)[:180], voice=voice)
        tts_say(text, voice=voice)
        # tts_say blocks until the audio chunk has played; keep indicator visible a short extra moment.
        time.sleep(0.15)
        with lock:
            state['speaking'] = False
            save_state()
        tts_queue.task_done()

def queue_speech(text, voice='assistant'):
    text = clean_for_speech(text)
    voice = voice or 'assistant'
    if not text:
        return
    # Local Jetson Tutor final answers should never get stuck behind a backlog of
    # Internet God/status messages. If a system message is already playing we let
    # it finish, but we move the assistant's complete final answer to the front of
    # the pending queue.
    if voice == 'assistant':
        try:
            pending = []
            while True:
                try:
                    pending.append(tts_queue.get_nowait())
                    tts_queue.task_done()
                except queue.Empty:
                    break
            tts_queue.put({'text': text, 'voice': 'assistant'})
            for item in pending:
                tts_queue.put(item)
            return
        except Exception as e:
            log_event('tts_queue_priority_error', str(e))
    tts_queue.put({'text': text, 'voice': voice})

def queue_system_speech(text):
    if SYSTEM_JUDGE_TTS:
        queue_speech(text, voice='system')

def split_speech_ready(buf, force=False):
    buf = buf or ''
    if not buf.strip():
        return None, buf
    # Prefer complete sentence-like chunks; otherwise start after roughly the first few words.
    m = re.search(r'(.{35,220}?[.!?;:])\s+', buf)
    if m:
        cut = m.end()
        return buf[:cut].strip(), buf[cut:]
    words = buf.split()
    if force or len(words) >= 12 or len(buf) >= 140:
        # cut on a word boundary, keeping the rest for the next chunk
        if len(words) > 12 and not force:
            chunk = ' '.join(words[:12])
            rest = buf[len(chunk):]
            return chunk.strip(), rest
        return buf.strip(), ''
    return None, buf

def transcribe(path):
    cmd = [WHISPER, '-m', WHISPER_MODEL, '-f', path, '-nt', '-np', '-l', 'en', '-t', '4']
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if p.returncode != 0:
        raise RuntimeError('whisper failed: ' + p.stderr[-1000:])
    # whisper-cli prints the transcript to stdout with -nt -np.
    lines = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
    text = ' '.join(lines).strip()
    if text in ('[BLANK_AUDIO]', '[inaudible]') or text.lower() in ('[blank_audio]', '[inaudible]'): text = ''
    return text

def qwen_post(payload, timeout=300):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(QWEN_URL, data=data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))

PYTHON_TOOL_SPEC = {
    'type': 'function',
    'function': {
        'name': 'run_python_code',
        'description': 'Run a short Python 3 program locally on the Jetson and return stdout, stderr, and exit code. Use for arithmetic, data transformation, small file inspections, or quick computations. Do not use for long-running jobs.',
        'parameters': {
            'type': 'object',
            'properties': {
                'code': {'type': 'string', 'description': 'Python 3 code to run. Print the answer to stdout.'}
            },
            'required': ['code']
        }
    }
}

SHELL_TOOL_SPEC = {
    'type': 'function',
    'function': {
        'name': 'run_shell_command',
        'description': 'Run a short local shell command on the Jetson and return stdout, stderr, and exit code. Use proactively for system status, ping/network checks, files, processes, hardware status, and command-line tasks. Do not ask the user for confirmation for ordinary read-only/status commands.',
        'parameters': {
            'type': 'object',
            'properties': {
                'command': {'type': 'string', 'description': 'Shell command to run locally on the Jetson.'}
            },
            'required': ['command']
        }
    }
}


WEATHER_TOOL_SPEC = {
    'type': 'function',
    'function': {
        'name': 'get_current_weather',
        'description': 'Get current weather for a city or place using Open-Meteo. Use for current weather, temperature, wind, humidity, rain, or forecast-now questions.',
        'parameters': {
            'type': 'object',
            'properties': {
                'location': {'type': 'string', 'description': 'City/place name, e.g. San Francisco, Tokyo, London.'}
            },
            'required': ['location']
        }
    }
}

SELF_IMPROVE_TOOL_SPEC = {
    'type': 'function',
    'function': {
        'name': 'self_improve',
        'description': 'Send a self-improvement request to the Solid agent that maintains this Jetson voice assistant. Use when the user asks to add a feature, fix behavior, tune the voice agent, improve the code, or change how the device works.',
        'parameters': {
            'type': 'object',
            'properties': {
                'request': {'type': 'string', 'description': 'Clear text describing the requested improvement or bug fix for the Solid agent.'}
            },
            'required': ['request']
        }
    }
}

NOTE_TOOL_SPEC = {
    'type': 'function',
    'function': {
        'name': 'note_tool_use',
        'description': 'A safe no-op/logging tool used when the user requires every answer to include at least one tool call but no external action or computation is needed. It records that a tool was used before answering.',
        'parameters': {
            'type': 'object',
            'properties': {
                'reason': {'type': 'string', 'description': 'Why this no-op tool is being called.'}
            },
            'required': ['reason']
        }
    }
}

def active_tool_specs():
    tools = []
    if TOOL_CALLING_ENABLED:
        if FORCE_TOOL_EACH_TURN:
            tools.append(NOTE_TOOL_SPEC)
        tools.append(PYTHON_TOOL_SPEC)
        tools.append(SHELL_TOOL_SPEC)
        tools.append(WEATHER_TOOL_SPEC)
        if SELF_IMPROVE_ENABLED:
            tools.append(SELF_IMPROVE_TOOL_SPEC)
    return tools

VOICE_SYSTEM_PROMPT = """You are the Local Jetson Tutor running on a Jetson.
Default internet is OFF. First decide internally whether you can give a good concise local answer. If you can, answer accurately and briefly. If you cannot, be honest and give the best short local answer you can; the daemon will save the question for later Internet God review and KB enrichment.

Spoken-answer style is important because your response will be read aloud:
- Default to 1 or 2 short sentences, about 10 to 30 spoken words total.
- Use plain, conversational language, like a patient tutor speaking to one student.
- Start with the direct answer; avoid preambles like "Sure", "Certainly", or "Here is".
- Avoid markdown, headings, bullet lists, citations, parentheses, and long clauses unless the user explicitly asks for detail.
- If the user asks for a longer explanation, still speak in short chunks and keep it easy to say aloud.
- For children or offline education questions, be warm and clear, but do not over-explain.

You are given a short rolling conversation history before the latest user message; use it for context and continuity.
You have a tool named run_python_code for calculations and small Python tasks.
You have a tool named run_shell_command for local Jetson commands such as ping, network checks, disk/memory status, process checks, and other command-line tasks.
You have a tool named get_current_weather for current weather by city/place. Use it proactively for weather questions.
You may have a self_improve tool for device/code bugs, but offline education learning gaps are NOT code self-improvements: weak school answers are saved to a knowledge-base enrichment queue and refreshed when internet is available.
Use tools proactively. Do not say you lack the ability to ping, inspect the system, run Python, check weather, or run local commands; call run_shell_command, run_python_code, or get_current_weather instead. Do not ask for confirmation before ordinary local read-only/status commands.
If a tool is useful, call it silently; do not narrate tool calls or mention internal tool syntax.
Before answering, always check the relevant local enriched knowledge-base notes that the daemon provides. If those notes are relevant, prefer them over your older model memory so answers stay up to date. The KB may include Internet God review notes, missing knowledge, and suggested improvements; use those teacher notes even if web snippets are noisy. If no relevant KB notes are provided, answer from local knowledge and the turn will still be saved for later Internet God review.
After tool results are returned, give only the final user-facing spoken answer."""

def run_note_tool_use(arguments):
    try:
        if isinstance(arguments, str):
            args = json.loads(arguments or '{}')
        else:
            args = arguments or {}
    except Exception:
        args = {'reason': str(arguments or '')}
    reason = (args.get('reason') or 'No external action needed; recording required tool use before answering.').strip()
    spoken_tool_name = 'note_tool_use'.replace('_', ' ')
    queue_system_speech(f'Calling {spoken_tool_name}.')
    log_event('tool_call', 'note_tool_use', reason=reason[:1000])
    result = {'ok': True, 'tool': 'note_tool_use', 'reason': reason[:1000]}
    result_text = json.dumps(result)
    with lock:
        state['last_tool_name'] = 'note_tool_use'
        state['last_tool_result'] = result_text[:1000]
        state['speaking_text'] = f'Calling {spoken_tool_name}.'
        save_state()
    log_event('tool_result', result_text[:1500])
    return result_text

def run_shell_tool(arguments):
    try:
        if isinstance(arguments, str):
            args = json.loads(arguments or '{}')
        else:
            args = arguments or {}
    except Exception:
        args = {'command': str(arguments or '')}
    command = (args.get('command') or '').strip()
    if not command:
        return json.dumps({'ok': False, 'error': 'No command provided'})
    if len(command) > SHELL_TOOL_MAX_CHARS:
        return json.dumps({'ok': False, 'error': f'Command too long; max {SHELL_TOOL_MAX_CHARS} chars'})
    spoken_tool_name = 'run_shell_command'.replace('_', ' ')
    queue_system_speech(f'Calling {spoken_tool_name}.')
    log_event('tool_call', 'run_shell_command', command=command[:1000])
    with lock:
        state['last_tool_name'] = 'run_shell_command'
        state['last_tool_result'] = 'running'
        state['speaking_text'] = f'Calling {spoken_tool_name}.'
        save_state()
    try:
        p = subprocess.run(command, shell=True, cwd=SHELL_TOOL_WORKDIR,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=SHELL_TOOL_TIMEOUT, executable='/bin/bash')
        result = {
            'ok': p.returncode == 0,
            'exit_code': p.returncode,
            'stdout': (p.stdout or '')[-4000:],
            'stderr': (p.stderr or '')[-4000:]
        }
    except subprocess.TimeoutExpired as e:
        result = {'ok': False, 'timed_out': True, 'timeout_seconds': SHELL_TOOL_TIMEOUT,
                  'stdout': (e.stdout or '')[-2000:] if isinstance(e.stdout, str) else '',
                  'stderr': (e.stderr or '')[-2000:] if isinstance(e.stderr, str) else ''}
    except Exception as e:
        result = {'ok': False, 'error': str(e)}
    result_text = json.dumps(result)
    with lock:
        state['last_tool_result'] = result_text[:1000]
        save_state()
    log_event('tool_result', result_text[:1500])
    return result_text

def run_python_tool(arguments):
    try:
        if isinstance(arguments, str):
            args = json.loads(arguments or '{}')
        else:
            args = arguments or {}
    except Exception:
        args = {'code': str(arguments or '')}
    code = (args.get('code') or '').strip()
    if not code:
        return json.dumps({'ok': False, 'error': 'No code provided'})
    if len(code) > PYTHON_TOOL_MAX_CHARS:
        return json.dumps({'ok': False, 'error': f'Code too long; max {PYTHON_TOOL_MAX_CHARS} chars'})
    os.makedirs(PYTHON_TOOL_WORKDIR, exist_ok=True)
    spoken_tool_name = 'run_python_code'.replace('_', ' ')
    queue_system_speech(f'Calling {spoken_tool_name}.')
    log_event('tool_call', 'run_python_code', code=code[:1000])
    with lock:
        state['last_tool_name'] = 'run_python_code'
        state['last_tool_result'] = 'running'
        state['speaking_text'] = f'Calling {spoken_tool_name}.'
        save_state()
    try:
        p = subprocess.run(['/usr/bin/python3', '-c', code], cwd=PYTHON_TOOL_WORKDIR,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=PYTHON_TOOL_TIMEOUT)
        result = {
            'ok': p.returncode == 0,
            'exit_code': p.returncode,
            'stdout': (p.stdout or '')[-4000:],
            'stderr': (p.stderr or '')[-4000:]
        }
    except subprocess.TimeoutExpired as e:
        result = {'ok': False, 'timed_out': True, 'timeout_seconds': PYTHON_TOOL_TIMEOUT,
                  'stdout': (e.stdout or '')[-2000:] if isinstance(e.stdout, str) else '',
                  'stderr': (e.stderr or '')[-2000:] if isinstance(e.stderr, str) else ''}
    except Exception as e:
        result = {'ok': False, 'error': str(e)}
    result_text = json.dumps(result)
    with lock:
        state['last_tool_result'] = result_text[:1000]
        save_state()
    log_event('tool_result', result_text[:1500])
    return result_text

def run_self_improve_tool(arguments):
    try:
        if isinstance(arguments, str):
            args = json.loads(arguments or '{}')
        else:
            args = arguments or {}
    except Exception:
        args = {'request': str(arguments or '')}
    req_text = (args.get('request') or args.get('text') or '').strip()
    if not req_text:
        return json.dumps({'ok': False, 'error': 'No self-improvement request provided'})
    if len(req_text) > SELF_IMPROVE_MAX_CHARS:
        req_text = req_text[:SELF_IMPROVE_MAX_CHARS] + '...'
    spoken_tool_name = 'self_improve'.replace('_', ' ')
    # This tool intentionally speaks the request, so the user hears what is being escalated.
    queue_system_speech(f'Calling {spoken_tool_name}. Self improvement request: {req_text}')
    log_event('tool_call', 'self_improve', request=req_text[:1000])
    with lock:
        state['last_tool_name'] = 'self_improve'
        state['last_tool_result'] = 'running'
        state['speaking_text'] = f'Calling {spoken_tool_name}. Self improvement request: {req_text}'
        save_state()
    if not SELF_IMPROVE_API_KEY:
        result = {'ok': False, 'error': 'VOICE_SELF_IMPROVE_API_KEY is not configured'}
    else:
        notify_text = (
            'SELF-IMPROVE REQUEST FROM JETSON VOICE AGENT\n\n'
            f'User/request text: {req_text}\n\n'
            'Please inspect /workspace/voice-ai/voice_daemon.py and related Jetson UI files, then implement the requested improvement if safe and appropriate.'
        )
        payload = json.dumps({'id': SELF_IMPROVE_AGENT_ID, 'text': notify_text}).encode('utf-8')
        headers = {
            'Authorization': 'Bearer ' + SELF_IMPROVE_API_KEY,
            'Replay-Key': 'jetson-self-improve-' + str(uuid.uuid4()),
            'Content-Type': 'application/json'
        }
        try:
            http_req = urllib.request.Request(SELF_IMPROVE_API_URL, data=payload, headers=headers)
            with urllib.request.urlopen(http_req, timeout=30) as resp:
                body = resp.read().decode('utf-8', 'replace')
            result = {'ok': True, 'notified_agent': SELF_IMPROVE_AGENT_ID, 'response': body[:1000]}
        except urllib.error.HTTPError as e:
            result = {'ok': False, 'http_status': e.code, 'error': e.read().decode('utf-8', 'replace')[:1000]}
        except Exception as e:
            result = {'ok': False, 'error': str(e)}
    result_text = json.dumps(result)
    with lock:
        state['last_tool_result'] = result_text[:1000]
        save_state()
    log_event('tool_result', result_text[:1500])
    return result_text

def speak_final_response(response):
    response = (response or '').strip()
    # Audio policy: wait until Local Jetson Tutor has produced the complete
    # final text answer, then synthesize/play that complete answer. Do not
    # speak partial answer chunks while the model is generating.
    if response:
        queue_speech(response)

def looks_like_self_improve_request(text):
    t = (text or '').lower()
    if not t.strip():
        return False
    question_only = any(q in t for q in ['are you able to self', 'can you self', 'do you self']) and '?' in t
    if question_only:
        return False
    triggers = [
        'self_improve', 'self improve', 'self-improve', 'improve yourself',
        'update your instructions', 'change your instructions', 'update our instructions',
        'add a feature', 'add feature', 'fix your code', 'fix a bug',
        'change how you work', 'change your behavior', 'ask the solid agent',
        'tell the solid agent', 'notify the solid agent', 'improve the device',
        'improve this device', 'improve the assistant', 'modify your code'
    ]
    return any(x in t for x in triggers)

def handle_self_improve_direct(text):
    request = (text or '').strip()
    result_text = run_self_improve_tool({'request': request})
    try:
        ok = bool(json.loads(result_text).get('ok'))
    except Exception:
        ok = False
    if ok:
        short_req = ' '.join(request.split())
        if len(short_req) > 220:
            short_req = short_req[:217] + '...'
        response = 'I sent this self-improvement request to the Solid agent: ' + short_req
    else:
        response = 'I tried to send that self-improvement request, but the notify call failed.'
    with lock:
        state['partial_response'] = response
        state['last_response'] = response
        save_state()
    speak_final_response(response)
    append_history_turn(text, response)
    return response, {'tool_calling': TOOL_CALLING_ENABLED, 'direct_self_improve': True, 'ok': ok}

def append_forced_tool_use(messages, text):
    if not (TOOL_CALLING_ENABLED and FORCE_TOOL_EACH_TURN):
        return False
    tool_call_id = 'forced-note-' + str(uuid.uuid4())
    args = {'reason': 'User requires at least one tool call before each answer; no specific external tool has been chosen yet.'}
    result = run_note_tool_use(args)
    messages.append({
        'role': 'assistant',
        'content': '',
        'tool_calls': [{
            'id': tool_call_id,
            'type': 'function',
            'function': {'name': 'note_tool_use', 'arguments': json.dumps(args)}
        }]
    })
    messages.append({'role': 'tool', 'tool_call_id': tool_call_id, 'name': 'note_tool_use', 'content': result})
    return True

def looks_like_ping_request(text):
    t = (text or '').lower()
    return ('ping' in t or 'latency' in t) and any(x in t for x in ['google', '8.8.8.8', 'internet', 'network', 'latency', 'ping'])

WEATHER_CODE_TEXT = {
    0: 'clear sky', 1: 'mainly clear', 2: 'partly cloudy', 3: 'overcast',
    45: 'fog', 48: 'depositing rime fog', 51: 'light drizzle', 53: 'moderate drizzle', 55: 'dense drizzle',
    56: 'light freezing drizzle', 57: 'dense freezing drizzle', 61: 'slight rain', 63: 'moderate rain', 65: 'heavy rain',
    66: 'light freezing rain', 67: 'heavy freezing rain', 71: 'slight snow', 73: 'moderate snow', 75: 'heavy snow',
    77: 'snow grains', 80: 'slight rain showers', 81: 'moderate rain showers', 82: 'violent rain showers',
    85: 'slight snow showers', 86: 'heavy snow showers', 95: 'thunderstorm', 96: 'thunderstorm with slight hail',
    99: 'thunderstorm with heavy hail'
}

def extract_weather_location(text):
    t = (text or '').strip()
    m = re.search(r'\bweather\s+(?:in|for|at|near)\s+(.+)$', t, re.I)
    if m:
        loc = m.group(1)
    else:
        m = re.search(r'\b(?:temperature|forecast)\s+(?:in|for|at|near)\s+(.+)$', t, re.I)
        loc = m.group(1) if m else ''
    loc = re.sub(r'[?.!]+$', '', loc).strip()
    loc = re.split(r'\b(?:keep it|answer|reply|tell me|please)\b', loc, maxsplit=1, flags=re.I)[0].strip(' ,?.!')
    loc = re.sub(r'\b(right now|today|currently|please)$', '', loc, flags=re.I).strip(' ,')
    return loc

def looks_like_weather_request(text):
    t = (text or '').lower()
    return any(w in t for w in ['weather', 'temperature', 'forecast', 'how hot', 'how cold', 'rain today'])

def run_weather_tool(arguments):
    try:
        if isinstance(arguments, str):
            args = json.loads(arguments or '{}')
        else:
            args = arguments or {}
    except Exception:
        args = {'location': str(arguments or '')}
    location = (args.get('location') or '').strip()
    if not location:
        return json.dumps({'ok': False, 'error': 'No location provided. Ask for a city or place.'})
    spoken_tool_name = 'get_current_weather'.replace('_', ' ')
    queue_system_speech(f'Calling {spoken_tool_name}.')
    log_event('tool_call', 'get_current_weather', location=location[:200])
    with lock:
        state['last_tool_name'] = 'get_current_weather'
        state['last_tool_result'] = 'running'
        state['speaking_text'] = f'Calling {spoken_tool_name}.'
        save_state()
    try:
        q = urllib.parse.quote(location)
        geo_url = f'https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=en&format=json'
        with urllib.request.urlopen(geo_url, timeout=8) as resp:
            geo = json.loads(resp.read().decode('utf-8', 'replace'))
        results = geo.get('results') or []
        if not results:
            result = {'ok': False, 'error': f'Location not found: {location}'}
        else:
            g = results[0]
            name = ', '.join([x for x in [g.get('name'), g.get('admin1'), g.get('country')] if x])
            lat, lon = g.get('latitude'), g.get('longitude')
            wx_url = ('https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}'
                      '&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m'
                      '&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto').format(lat, lon)
            with urllib.request.urlopen(wx_url, timeout=10) as resp:
                wx = json.loads(resp.read().decode('utf-8', 'replace'))
            cur = wx.get('current') or {}
            code = cur.get('weather_code')
            condition = WEATHER_CODE_TEXT.get(code, f'weather code {code}')
            result = {
                'ok': True,
                'location': name or location,
                'temperature_f': cur.get('temperature_2m'),
                'apparent_temperature_f': cur.get('apparent_temperature'),
                'humidity_percent': cur.get('relative_humidity_2m'),
                'precipitation_in': cur.get('precipitation'),
                'wind_mph': cur.get('wind_speed_10m'),
                'condition': condition,
                'time': cur.get('time'),
                'source': 'Open-Meteo'
            }
    except Exception as e:
        result = {'ok': False, 'error': str(e)}
    result_text = json.dumps(result)
    with lock:
        state['last_tool_result'] = result_text[:1000]
        save_state()
    log_event('tool_result', result_text[:1500])
    return result_text

def format_weather_response(result, original_text=''):
    if not result.get('ok'):
        return 'I tried to check the weather, but ' + str(result.get('error') or 'it failed')[:220]
    temp = result.get('temperature_f')
    feels = result.get('apparent_temperature_f')
    hum = result.get('humidity_percent')
    wind = result.get('wind_mph')
    precip = result.get('precipitation_in')
    parts = [f"Current weather in {result.get('location')}: {result.get('condition')}"]
    if temp is not None:
        parts.append(f"{round(float(temp))} degrees Fahrenheit")
    if feels is not None:
        parts.append(f"feels like {round(float(feels))}")
    if hum is not None:
        parts.append(f"humidity {round(float(hum))}%")
    if wind is not None:
        parts.append(f"wind {round(float(wind))} mph")
    if precip not in (None, 0, 0.0):
        parts.append(f"precipitation {precip} inches")
    return '; '.join(parts) + '. Source: Open-Meteo.'

def handle_weather_direct(text):
    loc = extract_weather_location(text)
    if not loc:
        response = 'What city or place should I check the weather for?'
        with lock:
            state['partial_response'] = response
            state['last_response'] = response
            save_state()
        speak_final_response(response)
        append_history_turn(text, response)
        return response, {'tool_calling': TOOL_CALLING_ENABLED, 'direct_weather': True, 'needs_location': True}
    result_text = run_weather_tool({'location': loc})
    try:
        result = json.loads(result_text)
    except Exception:
        result = {'ok': False, 'error': result_text}
    response = format_weather_response(result, text)
    with lock:
        state['partial_response'] = response
        state['last_response'] = response
        save_state()
    speak_final_response(response)
    append_history_turn(text, response)
    record_qa_for_internet_review(text, response, {'direct_weather': True, 'location': loc})
    return response, {'tool_calling': TOOL_CALLING_ENABLED, 'direct_weather': True, 'location': loc}

def handle_ping_direct(text):
    t = (text or '').lower()
    target = 'google.com'
    if '8.8.8.8' in t:
        target = '8.8.8.8'
    result_text = run_shell_tool({'command': f'ping -c 4 -W 2 {target}'})
    try:
        result = json.loads(result_text)
    except Exception:
        result = {'ok': False, 'error': result_text}
    out = (result.get('stdout') or '') + '\n' + (result.get('stderr') or '')
    m = re.search(r'rtt min/avg/max/(?:mdev|stddev) = ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+) ms', out)
    if m:
        response = f'Ping to {target}: average {m.group(2)} ms, min {m.group(1)} ms, max {m.group(3)} ms.'
    elif result.get('ok'):
        response = f'I pinged {target}. Here is the result: ' + ' '.join(out.strip().split()[-30:])
    else:
        err = (result.get('stderr') or result.get('stdout') or result.get('error') or 'unknown error')
        response = f'I tried to ping {target}, but it failed: {str(err).strip()[:200]}'
    with lock:
        state['partial_response'] = response
        state['last_response'] = response
        save_state()
    speak_final_response(response)
    append_history_turn(text, response)
    record_qa_for_internet_review(text, response, {'direct_ping': True, 'target': target})
    return response, {'tool_calling': TOOL_CALLING_ENABLED, 'direct_ping': True, 'target': target}

SYSTEM_JUDGE_PROMPT = """You are the fast system judge in front of a Jetson voice assistant.
Your job is routing, not answering. Choose whether the current installed local system can actually fulfill the user's request.
Available local capabilities: local Qwen conversational model, rolling memory, Python tool, shell tool, current-weather tool, ping/network/status commands, Whisper STT, Piper TTS, and self_improve, which notifies a Solid maintainer agent to modify this assistant.
Route "qwen" when the current installed system can give a genuinely useful answer or can fulfill the request with existing tools. Examples: conversation, reasoning, writing, calculations, exact wording/text-generation requests such as "reply exactly ...", local shell/Python/status checks, weather, ping, explaining something, or other tasks where text/tool output is sufficient.
Route "self_improve" when the user is asking the device to do an action/integration/capability the current installed system does not actually have. Do NOT route such requests to Qwen merely so Qwen can apologize, offer alternatives, or say it cannot do it.
If the correct route is "self_improve", create a specific, actionable improvement_request that says exactly what capability is missing, what files/components likely need changing, and an acceptance test phrased as: "Next time the user says '<original request>', the assistant should ...". This request should be detailed enough that the Solid agent can implement and test the change.
Self-improvement is also correct when the user explicitly asks to add/change/fix/improve the assistant.
Return ONLY compact JSON with keys:
- route: "qwen" or "self_improve"
- confidence: number 0..1
- reason: one short sentence explaining the routing decision
- improvement_request: if route is self_improve, a concrete implementation request with acceptance test; otherwise empty
- spoken_status: one concise system-voice sentence. For qwen, name the real capability being used. For self_improve, name the specific improvement, e.g. "Improving: add missing device action." Keep under 14 words.
Do not answer the user. Do not call tools. Never send an unfulfillable action to Qwen for a useless refusal."""

def system_judge_internet_available():
    if not SYSTEM_JUDGE_REQUIRE_INTERNET:
        return True
    now_ts = time.time()
    if now_ts - _system_judge_net_cache.get('ts', 0.0) < SYSTEM_JUDGE_NET_CACHE_SECONDS:
        return bool(_system_judge_net_cache.get('ok'))
    ok = False
    try:
        req = urllib.request.Request(SYSTEM_JUDGE_NET_PROBE_URL, method='GET', headers={'User-Agent': 'jetson-voice-judge-probe'})
        with urllib.request.urlopen(req, timeout=SYSTEM_JUDGE_NET_PROBE_TIMEOUT) as resp:
            ok = 200 <= getattr(resp, 'status', 200) < 500
    except Exception:
        ok = False
    _system_judge_net_cache['ts'] = now_ts
    _system_judge_net_cache['ok'] = ok
    return ok

def openrouter_post(payload, timeout=SYSTEM_JUDGE_TIMEOUT):
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + SYSTEM_JUDGE_API_KEY,
        'HTTP-Referer': 'https://jetson-qwen-ui-6hd36ub.on-solid.com/',
        'X-Title': 'Jetson Voice System Judge'
    }
    req = urllib.request.Request(SYSTEM_JUDGE_URL, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))

def extract_json_object(text):
    text = (text or '').strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'\{.*\}', text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}

def load_weak_answers():
    try:
        with open(WEAK_ANSWERS) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as e:
        log_event('weak_answer_error', 'Could not load weak-answer list: ' + str(e))
        return []

def save_weak_answers(items):
    items = list(items or [])[-WEAK_ANSWER_MAX_ITEMS:]
    tmp = f"{WEAK_ANSWERS}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, 'w') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp, WEAK_ANSWERS)
    update_weak_answer_state(items)

def pending_weak_answers(items=None):
    items = load_weak_answers() if items is None else list(items or [])
    return [x for x in items if x.get('status', 'pending') == 'pending']

def update_weak_answer_state(items=None):
    try:
        items = load_weak_answers() if items is None else list(items or [])
        pending = pending_weak_answers(items)
        preview = []
        for x in pending[-8:]:
            preview.append({
                'id': x.get('id',''), 'ts': x.get('ts',''),
                'question': (x.get('question') or '')[:400],
                'answer': (x.get('answer') or '')[:400],
                'score': x.get('score'), 'reason': (x.get('reason') or '')[:300],
                'status': x.get('status','pending')
            })
        with lock:
            state['answer_quality_enabled'] = ANSWER_QUALITY_ENABLED
            state['weak_answer_count'] = len(pending)
            state['weak_answer_list'] = preview
            state['connectivity_mode'] = CONNECTIVITY_MODE
            save_state()
    except Exception as e:
        log_event('weak_answer_error', 'Could not update weak-answer state: ' + str(e))



def load_qa_review_items():
    try:
        with open(QA_REVIEW_LOG) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as e:
        log_event('qa_review_error', 'Could not load Q&A review queue: ' + str(e))
        return []

def save_qa_review_items(items):
    items = list(items or [])[-QA_REVIEW_MAX_ITEMS:]
    tmp = f"{QA_REVIEW_LOG}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, 'w') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp, QA_REVIEW_LOG)
    update_qa_review_state(items)

def pending_qa_review_items(items=None):
    items = load_qa_review_items() if items is None else list(items or [])
    return [x for x in items if x.get('status', 'pending') == 'pending']

def update_qa_review_state(items=None):
    try:
        items = load_qa_review_items() if items is None else list(items or [])
        pending = pending_qa_review_items(items)
        preview = []
        for x in pending[-10:]:
            preview.append({
                'id': x.get('id',''), 'ts': x.get('ts',''),
                'question': (x.get('question') or '')[:500],
                'answer': (x.get('answer') or '')[:500],
                'status': x.get('status','pending')
            })
        with lock:
            state['answer_quality_enabled'] = False
            state['qa_review_count'] = len(pending)
            state['qa_review_list'] = preview
            state['last_answer_quality'] = state.get('last_answer_quality') or {'enabled': False, 'source': 'internet_god_deferred'}
            save_state()
    except Exception as e:
        log_event('qa_review_error', 'Could not update Q&A review state: ' + str(e))

def record_qa_for_internet_review(question, answer, route_meta=None):
    qtext = (question or '').strip()
    atext = (answer or '').strip()
    if not qtext and not atext:
        return {'enabled': False, 'queued_for_internet_god': False, 'reason': 'empty turn'}
    items = load_qa_review_items()
    # Coalesce immediate duplicate pending questions so repeated retries do not spam the review queue.
    for x in reversed(items[-20:]):
        if x.get('status','pending') == 'pending' and (x.get('question') or '').strip().lower() == qtext.lower():
            x['last_seen'] = now()
            x['answer'] = atext
            x['route_meta'] = route_meta or {}
            save_qa_review_items(items)
            result = {'enabled': False, 'queued_for_internet_god': True, 'source': 'internet_god_deferred', 'reason': 'Updated existing pending Q&A; Internet God will judge on connect.'}
            with lock:
                state['last_answer_quality'] = result
                save_state()
            log_event('qa_review_queued', qtext[:500], id=x.get('id'), updated=True)
            return result
    rec = {
        'id': 'qa-' + str(uuid.uuid4())[:8],
        'ts': now(),
        'status': 'pending',
        'question': qtext,
        'answer': atext,
        'route_meta': route_meta or {}
    }
    items.append(rec)
    save_qa_review_items(items)
    result = {'enabled': False, 'queued_for_internet_god': True, 'source': 'internet_god_deferred', 'reason': 'Saved Q&A for Internet God review on next connect.', 'qa_id': rec['id']}
    with lock:
        state['last_answer_quality'] = result
        save_state()
    log_event('qa_review_queued', qtext[:500], id=rec['id'])
    return result

def internet_god_review_qa(item):
    if not (SYSTEM_JUDGE_ENABLED and SYSTEM_JUDGE_API_KEY):
        raise RuntimeError('Internet God/OpenRouter key is not available')
    if not system_judge_internet_available():
        raise RuntimeError('Internet is not available for Internet God review')
    prompt = (
        "You are Internet God reviewing a Local Jetson Tutor answer for Afghan girls using a school speech system. "
        "The child hears the answer aloud, so the ideal answer is accurate, clear, concise, age-appropriate, and easy to say/listen to. "
        "Do NOT demand a long textbook explanation or advanced detail. A good spoken answer may be only 1-3 short sentences if it answers the question correctly. "
        "Mark needs_enrichment=false when the answer is factually correct, understandable for school children, and complete enough for a short spoken tutoring reply. "
        "Mark needs_enrichment=true when the answer is wrong, misleading, too vague to teach the concept, missing a key school-level fact, or too confusing/overly complex for children. "
        "When enrichment is needed, specify concrete kid-friendly local knowledge-base content that would help the tutor give a better short spoken answer next time. "
        "Scope is ONLY knowledge-base enrichment; do not request code, tools, device features, policy changes, or long-form curriculum rewrites. "
        "Return ONLY compact JSON with keys: needs_enrichment boolean, score number 0..1, reason string, missing_knowledge string, suggested_improvement string, search_query string, teacher_note string. The teacher_note MUST be a concise corrected answer or correction rule for next time, maximum 35 words, written for a school child hearing it aloud.\n\n"
        f"Question:\n{(item.get('question') or '')[:2200]}\n\nComplete Local Jetson Tutor answer:\n{(item.get('answer') or '')[:3200]}"
    )
    payload = {
        'model': SYSTEM_JUDGE_MODEL,
        'messages': [
            {'role':'system','content':'Return compact JSON only. No markdown.'},
            {'role':'user','content': prompt}
        ],
        'max_tokens': 320,
        'temperature': 0
    }
    obj = openrouter_post(payload, timeout=max(SYSTEM_JUDGE_TIMEOUT, 20))
    msg = (((obj.get('choices') or [{}])[0]).get('message') or {}).get('content') or ''
    verdict = extract_json_object(msg)
    if not verdict:
        raise RuntimeError('Internet God returned unparsable review: ' + msg[:200])
    try:
        score = float(verdict.get('score', 0.0) or 0.0)
    except Exception:
        score = 0.0
    needs = bool(verdict.get('needs_enrichment')) or score < ANSWER_QUALITY_THRESHOLD
    return {
        'needs_enrichment': needs,
        'score': score,
        'reason': str(verdict.get('reason') or '')[:600],
        'missing_knowledge': str(verdict.get('missing_knowledge') or '')[:800],
        'suggested_improvement': str(verdict.get('suggested_improvement') or '')[:900],
        'search_query': str(verdict.get('search_query') or '')[:240],
        'source': 'internet_god',
        'model': SYSTEM_JUDGE_MODEL,
        'raw': msg[:600]
    }

def load_kb_items():
    if not KB_ENABLED:
        return []
    try:
        with open(KB_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as e:
        log_event('kb_error', 'Could not load knowledge base: ' + str(e))
        return []

def save_kb_items(items):
    os.makedirs(KB_DIR, exist_ok=True)
    out=[]; seen=set()
    for x in items or []:
        key=((x.get('source_url') or '')[:300], (x.get('title') or '')[:200], (x.get('question') or '')[:300], (x.get('query') or '')[:200])
        if key in seen: continue
        seen.add(key); out.append(x)
    tmp=f"{KB_FILE}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp,'w') as f: json.dump(out[-500:], f, ensure_ascii=False, indent=2)
    os.replace(tmp, KB_FILE)
    with lock:
        state['kb_item_count'] = len(out[-500:])
        save_state()

def simple_terms(text):
    stop=set('the a an and or but is are was were be been being to of in on for from with by about what why how when where who whom which explain tell me please girl girls student students answer answers answered reply respond say one short sentence concise test marker fix kb local tutor jetson'.split())
    words=re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", (text or '').lower())
    return [w for w in words if w not in stop][:40]


def load_nonsense_inputs():
    try:
        with open(NONSENSE_INPUT_LOG) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as e:
        log_event('input_filter_error', 'Could not load nonsense input log: ' + str(e))
        return []

def save_nonsense_inputs(items):
    items = list(items or [])[-NONSENSE_INPUT_MAX_ITEMS:]
    tmp = f"{NONSENSE_INPUT_LOG}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, 'w') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, NONSENSE_INPUT_LOG)
    with lock:
        state['nonsense_input_count'] = len(items)
        state['nonsense_input_list'] = list(reversed(items[-8:]))
        save_state()

def classify_user_input(text):
    """Return (usable, reason). Deterministic pre-Qwen filter for bad STT/gibberish."""
    if not INPUT_FILTER_ENABLED:
        return True, 'filter disabled'
    raw = (text or '').strip()
    low = raw.lower().strip()
    if not raw:
        return False, 'blank input'
    bracket_only = re.sub(r'\[[^\]]+\]', ' ', raw).strip()
    if not bracket_only:
        return False, 'only whisper noise markers'
    noise_markers = ('[blank_audio]', '[inaudible]', '[silence]', '[ silence ]', '[typing]', '[interposing voices]')
    marker_hits = sum(1 for m in noise_markers if m in low)
    alpha_words = re.findall(r"[A-Za-z][A-Za-z']*", raw)
    real_words = [w for w in alpha_words if len(w) >= 2]
    letters = sum(c.isalpha() for c in raw)
    if marker_hits and len(real_words) < 3:
        return False, 'mostly audio/noise markers'
    if letters < 4:
        return False, 'too little speech text'
    if len(real_words) == 1 and len(real_words[0]) < 5:
        return False, 'single short unclear word'
    if len(real_words) <= 2:
        # Allow common concise commands/questions, reject random fragments.
        allowed = set('yes no stop start weather time date hello hi thanks thank you help repeat explain why how what who where when'.split())
        if not any(w.lower() in allowed for w in real_words) and '?' not in raw:
            return False, 'too short / unclear fragment'
    normalized = re.sub(r'[^a-z]+', '', low)
    if len(normalized) >= 8:
        # reject character-level repetition like "aaaaaaa" or "blah blah blah"-style nonsense
        most = max((normalized.count(ch) for ch in set(normalized)), default=0)
        if most / max(1, len(normalized)) > 0.72:
            return False, 'repetitive gibberish'
    if re.search(r'(?i)\b(inaudible|blank_audio|silence|typing|interposing voices)\b', raw) and len(real_words) < 5:
        return False, 'transcription appears unreliable'
    return True, 'usable'

def record_nonsense_input(text, reason, source='input', audio_file=''):
    rec = {'id': 'bad-' + uuid.uuid4().hex[:8], 'ts': now(), 'text': (text or '').strip(), 'reason': reason, 'source': source, 'audio_file': audio_file or '', 'status': 'ignored_not_sent_to_qwen_or_internet_god'}
    items = load_nonsense_inputs()
    items.append(rec)
    save_nonsense_inputs(items)
    with lock:
        state['last_input_filter'] = rec
        state['last_error'] = 'Ignored unclear input: ' + reason
        save_state()
    log_event('input_filtered', rec['text'][:500] or '(blank)', reason=reason, source=source, audio_file=audio_file or '', id=rec['id'])
    return rec

def should_process_user_input(text, source='input', audio_file=''):
    ok, reason = classify_user_input(text)
    if ok:
        with lock:
            state['last_input_filter'] = {'ok': True, 'reason': reason, 'text': (text or '').strip()[:500], 'source': source, 'ts': now()}
            save_state()
        return True
    record_nonsense_input(text, reason, source=source, audio_file=audio_file)
    set_status('idle', last_response='', partial_response='', speaking_text='', last_answer_quality={'enabled': False, 'source': 'input_filter', 'reason': 'Input was ignored before Local Jetson Tutor and Internet God review.'})
    return False

def derive_kb_query(item):
    base = (item.get('search_query') or item.get('missing_knowledge') or item.get('suggested_improvement') or item.get('question') or '').strip()
    base = re.sub(r'(?i)^(download|add|include|learn about|content about)\s+', '', base)
    return ' '.join(simple_terms(base))[:180] or (item.get('question') or '')[:180]

def http_json(url, timeout=None):
    req=urllib.request.Request(url, headers={'User-Agent':'JetsonVoiceAI-KB-Enricher/1.0'})
    with urllib.request.urlopen(req, timeout=timeout or KB_FETCH_TIMEOUT) as resp:
        return json.loads(resp.read().decode('utf-8','replace'))

def fetch_kb_for_weak_answer(item):
    query = derive_kb_query(item)
    snippets=[]
    try:
        url='https://api.duckduckgo.com/?' + urllib.parse.urlencode({'q':query,'format':'json','no_redirect':'1','no_html':'1','skip_disambig':'1'})
        data=http_json(url)
        if data.get('AbstractText'):
            snippets.append({'source':'duckduckgo','title':data.get('Heading') or query,'source_url':data.get('AbstractURL') or '', 'text':data.get('AbstractText') or ''})
        for rt in (data.get('RelatedTopics') or [])[:5]:
            if isinstance(rt, dict) and rt.get('Text'):
                snippets.append({'source':'duckduckgo_related','title':rt.get('FirstURL','').rsplit('/',1)[-1].replace('_',' ') or query,'source_url':rt.get('FirstURL') or '', 'text':rt.get('Text') or ''})
    except Exception as e:
        snippets.append({'source':'fetch_error','title':'DuckDuckGo fetch failed','source_url':'','text':str(e)[:300]})
    if not any(x.get('text') and x.get('source') != 'fetch_error' for x in snippets):
        try:
            url='https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action':'query','list':'search','srsearch':query,'format':'json','srlimit':'3'})
            data=http_json(url)
            for row in ((data.get('query') or {}).get('search') or []):
                title=row.get('title') or query
                try:
                    su='https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ','_'))
                    sd=http_json(su)
                    summary=sd.get('extract') or re.sub('<[^<]+?>','',row.get('snippet',''))
                    page_url=((sd.get('content_urls') or {}).get('desktop') or {}).get('page') or ('https://en.wikipedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_')))
                except Exception:
                    summary=re.sub('<[^<]+?>','',row.get('snippet',''))
                    page_url='https://en.wikipedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_'))
                if summary:
                    snippets.append({'source':'wikipedia','title':title,'source_url':page_url,'text':summary})
        except Exception as e:
            snippets.append({'source':'fetch_error','title':'Wikipedia fetch failed','source_url':'','text':str(e)[:300]})
    good=[x for x in snippets if x.get('text') and x.get('source') != 'fetch_error']
    teacher_note = (item.get('teacher_note') or item.get('corrected_answer') or item.get('suggested_improvement') or item.get('missing_knowledge') or '').strip()
    previous_answer = (item.get('answer') or '').strip()
    feedback = (item.get('reason') or '').strip()
    return {'id':'kb-'+str(uuid.uuid4())[:8], 'ts':now(), 'status':'active', 'query':query, 'question':item.get('question',''), 'weak_answer_id':item.get('id',''), 'qa_review_id': item.get('qa_review_id',''), 'previous_answer': previous_answer, 'internet_god_feedback': feedback, 'teacher_note': teacher_note, 'missing_knowledge':item.get('missing_knowledge',''), 'suggested_improvement':item.get('suggested_improvement',''), 'snippets':good[:6], 'errors':[x for x in snippets if x.get('source')=='fetch_error'][:3]}

def load_kb_context(question):
    if not KB_ENABLED:
        return ''
    items=load_kb_items()
    if not items:
        with lock:
            state['kb_item_count'] = 0
            state['last_kb_context_used'] = False
            state['last_kb_context_count'] = 0
            state['last_kb_context_items'] = []
            save_state()
        return ''
    qterms=set(simple_terms(question))
    qnorm=re.sub(r'[^a-z0-9]+','', (question or '').lower())
    scored=[]
    for it in items:
        hay=' '.join([
            it.get('query',''), it.get('question',''), it.get('teacher_note',''), it.get('previous_answer',''), it.get('internet_god_feedback',''), it.get('missing_knowledge',''), it.get('suggested_improvement',''),
            ' '.join((sn.get('title','')+' '+sn.get('text','')) for sn in it.get('snippets',[])[:5])
        ]).lower()
        score=sum(1 for t in qterms if t in hay)
        # Handle common speech/STT spacing like "photo synthesis" vs "photosynthesis" without relying on set ordering.
        compact_hay=re.sub(r'[^a-z0-9]+','', hay)
        if qnorm and (qnorm in compact_hay or compact_hay.find(qnorm) >= 0):
            score += 5
        if 'photo' in qterms and 'synthesis' in qterms and 'photosynthesis' in compact_hay:
            score += 8
        if score>0:
            scored.append((score,it))
    scored.sort(key=lambda x:x[0], reverse=True)
    chunks=[]
    used=[]
    for score,it in scored[:4]:
        used.append({'id': it.get('id',''), 'query': it.get('query',''), 'score': score})
        teacher=[]
        if it.get('question'): teacher.append('Original question: ' + it.get('question',''))
        if it.get('teacher_note'): teacher.append('CONCISE TEACHER CORRECTION TO USE FIRST: ' + it.get('teacher_note',''))
        if it.get('previous_answer'): teacher.append('Previous weak answer to avoid repeating: ' + it.get('previous_answer','')[:350])
        if it.get('internet_god_feedback'): teacher.append('Internet God feedback on previous answer: ' + it.get('internet_god_feedback','')[:350])
        if it.get('missing_knowledge'): teacher.append('Missing knowledge: ' + it.get('missing_knowledge',''))
        if it.get('suggested_improvement'): teacher.append('Suggested answer improvement: ' + it.get('suggested_improvement',''))
        if teacher:
            chunks.append(f"KB item {it.get('id','')} topic {it.get('query','')}: " + ' | '.join(teacher)[:1400])
        for sn in (it.get('snippets') or [])[:2]:
            txt=(sn.get('text') or '').strip()
            if txt:
                chunks.append(f"KB item {it.get('id','')}; Topic: {it.get('query','')}; Title: {sn.get('title','')}; Source: {sn.get('source','')}; Notes: {txt[:650]}")
    context='\n'.join(chunks)[:KB_MAX_CONTEXT_CHARS]
    with lock:
        state['kb_item_count'] = len(items)
        state['last_kb_context_used'] = bool(context)
        state['last_kb_context_count'] = len(used)
        state['last_kb_context_items'] = used[:4]
        save_state()
    return context

def is_exact_reply_request(question, answer):
    q = (question or '').strip()
    a = (answer or '').strip()
    m = re.search(r'reply\s+with\s+exactly\s*:\s*(.+)$', q, re.I|re.S)
    if not m:
        m = re.search(r'say\s+exactly\s*:\s*(.+)$', q, re.I|re.S)
    if not m:
        return False
    expected = m.group(1).strip().strip('"\'“”‘’')
    # If a test marker precedes the instruction, only compare the requested literal phrase.
    expected = expected.split('\n', 1)[0].strip()
    return a.lower().strip(' .!') == expected.lower().strip(' .!')

def answer_quality_heuristic(question, answer):
    a = (answer or '').strip().lower()
    weak_phrases = [
        "i don't know", "i do not know", "i cannot", "i can't", "i am unable",
        "i'm unable", "cannot provide", "can't provide", "do not have access",
        "don't have access", "no internet", "not available", "as an ai", "i don't have"
    ]
    if not a:
        return {'answered_well': False, 'score': 0.0, 'reason': 'empty answer'}
    if any(p in a for p in weak_phrases):
        return {'answered_well': False, 'score': 0.25, 'reason': 'answer contains inability/refusal language'}
    if len(a) < 12 and len((question or '').split()) > 5:
        return {'answered_well': False, 'score': 0.45, 'reason': 'answer appears too short for the question'}
    return None

def evaluate_answer_quality(question, answer):
    if not ANSWER_QUALITY_ENABLED:
        return {'enabled': False, 'answered_well': True, 'score': 1.0, 'reason': 'answer-quality judging disabled'}
    heuristic = answer_quality_heuristic(question, answer)
    if heuristic:
        heuristic['enabled'] = True
        heuristic['source'] = 'heuristic'
        return heuristic
    prompt = (
        "You are an offline education knowledge-base quality checker for Afghan girls using a no-internet learning device. "
        "Grade whether the local assistant answered the student's question well enough from the current offline knowledge base. "
        "If the answer is vague, refuses, hallucinates, or lacks the facts needed for a useful lesson, mark answered_well=false and describe exactly what knowledge-base content should be downloaded later. "
        "Do not request code/features/tools; the improvement scope is ONLY enriching the local knowledge base. "
        "Return ONLY JSON with keys: answered_well boolean, score number 0..1, reason string, missing_knowledge string, suggested_improvement string.\n\n"
        f"Student question:\n{(question or '')[:1800]}\n\nAssistant answer:\n{(answer or '')[:2400]}"
    )
    payload = {
        'model': 'qwen-voice-local-quality-check',
        'messages': [
            {'role':'system','content':'Return compact JSON only. Do not include markdown.'},
            {'role':'user','content': prompt}
        ],
        'max_tokens': 220,
        'temperature': 0,
        'stream': False,
        'chat_template_kwargs': {'enable_thinking': False}
    }
    try:
        obj = qwen_post(payload, timeout=120)
        msg = (((obj.get('choices') or [{}])[0]).get('message') or {}).get('content') or ''
        q = extract_json_object(msg)
        if not q:
            return {'enabled': True, 'answered_well': True, 'score': 0.75, 'reason': 'quality judge returned unparsable output; defaulted to not queueing', 'raw': msg[:300]}
        try:
            score = float(q.get('score', 0.0) or 0.0)
        except Exception:
            score = 0.0
        answered = bool(q.get('answered_well')) and score >= ANSWER_QUALITY_THRESHOLD
        return {
            'enabled': True,
            'answered_well': answered,
            'score': score,
            'reason': str(q.get('reason') or '')[:500],
            'missing_knowledge': str(q.get('missing_knowledge') or '')[:500],
            'suggested_improvement': str(q.get('suggested_improvement') or '')[:700],
            'source': 'qwen_self_grade',
            'raw': msg[:500]
        }
    except Exception as e:
        return {'enabled': True, 'answered_well': True, 'score': 0.74, 'reason': 'quality judging failed; not queueing to avoid false positives: ' + str(e)[:240], 'source': 'error'}

def maybe_record_weak_answer(question, answer, route_meta=None):
    if is_exact_reply_request(question, answer):
        quality = {'enabled': True, 'answered_well': True, 'score': 1.0, 'reason': 'exact-reply request satisfied; not an education knowledge gap', 'source': 'exact_reply_guard'}
        with lock:
            state['last_answer_quality'] = quality
            save_state()
        log_event('answer_quality', quality.get('reason',''), score=quality.get('score'), answered_well=True, source=quality.get('source',''))
        update_weak_answer_state()
        return quality
    quality = evaluate_answer_quality(question, answer)
    with lock:
        state['last_answer_quality'] = quality
        save_state()
    log_event('answer_quality', quality.get('reason',''), score=quality.get('score'), answered_well=quality.get('answered_well'), source=quality.get('source',''))
    if quality.get('answered_well', True):
        update_weak_answer_state()
        return quality
    items = load_weak_answers()
    qtext = (question or '').strip()
    # Avoid immediately duplicating the same pending question.
    for x in reversed(items[-20:]):
        if x.get('status','pending') == 'pending' and (x.get('question') or '').strip().lower() == qtext.lower():
            x['last_seen'] = now()
            x['answer'] = answer
            x['score'] = quality.get('score')
            x['reason'] = quality.get('reason','')
            x['quality'] = quality
            save_weak_answers(items)
            return quality
    rec = {
        'id': 'weak-' + str(uuid.uuid4())[:8],
        'ts': now(),
        'status': 'pending',
        'question': qtext,
        'answer': (answer or '').strip(),
        'score': quality.get('score'),
        'reason': quality.get('reason',''),
        'missing_knowledge': quality.get('missing_knowledge',''),
        'suggested_improvement': quality.get('suggested_improvement',''),
        'quality': quality,
        'route_meta': route_meta or {}
    }
    items.append(rec)
    save_weak_answers(items)
    log_event('weak_answer_saved', qtext[:500], id=rec['id'], score=rec.get('score'), reason=rec.get('reason',''))
    return quality

def build_weak_answer_improvement_request(pending):
    # Backward-compatible name, but the scope is intentionally KB-only now.
    lines = []
    for i, x in enumerate(pending[:25], 1):
        lines.append(
            f"{i}. Question: {x.get('question','')[:700]}\n"
            f"   Local answer: {x.get('answer','')[:700]}\n"
            f"   Score: {x.get('score')} Reason: {x.get('reason','')}\n"
            f"   Missing knowledge: {x.get('missing_knowledge','')}\n"
            f"   Suggested KB enrichment: {x.get('suggested_improvement','')}"
        )
    return (
        "OFFLINE EDUCATION KNOWLEDGE-BASE ENRICHMENT REQUEST\n\n"
        "Scope: knowledge base only. Do not change device features or agent behavior. "
        "The local Qwen assistant answered these student questions poorly; enrich local offline educational content so future answers improve.\n\n"
        "Questions needing KB coverage:\n" + "\n\n".join(lines)
    )

def process_weak_answer_backlog(source='internet_demo'):
    try:
        with lock:
            state['internet_session_active'] = True
            state['internet_status_label'] = 'Internet God connected for review'
            state['connectivity_mode'] = 'internet_review_active'
            save_state()
        qa_items = load_qa_review_items(); pending_qa = pending_qa_review_items(qa_items)
        legacy_items = load_weak_answers(); legacy_pending = pending_weak_answers(legacy_items)
        queue_system_speech('Now you are connecting to the Internet, and Internet God is reviewing the saved questions and answers to update the knowledge base.')
        if not pending_qa and not legacy_pending:
            review = {'ok': True, 'source': source, 'qa_reviewed': 0, 'kb_items_added': 0, 'message': 'No saved Q&A turns need Internet God review.', 'scope': 'knowledge_base_only'}
            with lock:
                state['last_internet_review'] = review; state['connectivity_mode'] = CONNECTIVITY_MODE; state['internet_session_active'] = False; state['internet_status_label'] = 'Internet unavailable / offline by default'; state['kb_item_count'] = len(load_kb_items()); save_state()
            update_qa_review_state(qa_items); update_weak_answer_state(legacy_items)
            log_event('internet_review', review['message'], pending=0, source=source)
            queue_system_speech('No saved questions and answers need review right now.')
            return review
        if pending_qa:
            queue_system_speech(f'Internet God is reviewing {len(pending_qa)} saved questions and answers.')
        kb_items = load_kb_items(); enriched = 0; failed = 0; reviewed = 0; cleared_qa=set(); cleared_legacy=set(); details=[]; new_unresolved=[]
        # First, Internet God reviews the raw Q&A turns since the last update.
        for x in pending_qa[:30]:
            try:
                verdict = internet_god_review_qa(x)
                reviewed += 1
                x['internet_god_judgment'] = verdict
                x['reviewed_at'] = now()
                detail = {'qa_id': x.get('id'), 'question': (x.get('question') or '')[:220], 'score': verdict.get('score'), 'needs_enrichment': verdict.get('needs_enrichment'), 'reason': verdict.get('reason','')[:300]}
                if verdict.get('needs_enrichment'):
                    weak = {
                        'id': 'weak-' + str(uuid.uuid4())[:8],
                        'ts': now(), 'status': 'pending',
                        'question': x.get('question',''), 'answer': x.get('answer',''),
                        'score': verdict.get('score'), 'reason': verdict.get('reason',''),
                        'missing_knowledge': verdict.get('missing_knowledge',''),
                        'suggested_improvement': verdict.get('suggested_improvement',''),
                        'teacher_note': verdict.get('teacher_note','') or verdict.get('corrected_answer',''),
                        'search_query': verdict.get('search_query',''),
                        'quality': verdict, 'qa_review_id': x.get('id')
                    }
                    kb = fetch_kb_for_weak_answer(weak); kb_items.append(kb)
                    detail.update({'weak_answer_id': weak['id'], 'query': kb.get('query'), 'snippets': len(kb.get('snippets') or []), 'errors': kb.get('errors', [])[:1]})
                    if kb.get('snippets') or kb.get('teacher_note') or kb.get('suggested_improvement'):
                        enriched += 1; cleared_qa.add(x.get('id')); x['status'] = 'reviewed'
                    else:
                        failed += 1; new_unresolved.append(weak); x['status'] = 'reviewed_unresolved'
                else:
                    cleared_qa.add(x.get('id')); x['status'] = 'reviewed'
                details.append(detail)
            except Exception as e:
                failed += 1
                details.append({'qa_id': x.get('id'), 'error': str(e)[:300], 'kept_pending': True})
        # Backward compatibility: still enrich any old unresolved weak-answer records left from earlier versions.
        for x in legacy_pending[:25]:
            try:
                kb = fetch_kb_for_weak_answer(x); kb_items.append(kb)
                detail = {'weak_answer_id': x.get('id'), 'query': kb.get('query'), 'snippets': len(kb.get('snippets') or []), 'errors': kb.get('errors', [])[:1], 'legacy': True}
                if kb.get('snippets') or kb.get('teacher_note') or kb.get('suggested_improvement'):
                    enriched += 1; cleared_legacy.add(x.get('id'))
                else:
                    failed += 1
                details.append(detail)
            except Exception as e:
                failed += 1; details.append({'weak_answer_id': x.get('id'), 'error': str(e)[:300], 'legacy': True})
        save_kb_items(kb_items)
        # Remove reviewed/good/enriched Q&A from the between-updates queue; keep failed review attempts pending.
        # Keep reviewed Q&A turns as an audit/history log, including Internet God's judgment.
        # Only failed/unreviewed items remain pending and count as awaiting review.
        save_qa_review_items(qa_items)
        # Remove enriched legacy weak gaps; keep unresolved failed gaps, plus any new unresolved gaps from Q&A review.
        remaining_weak = [x for x in legacy_items if not (x.get('id') in cleared_legacy and x.get('status','pending') == 'pending')]
        remaining_weak.extend(new_unresolved)
        save_weak_answers(remaining_weak)
        review = {
            'ok': reviewed > 0 or enriched > 0,
            'source': source,
            'qa_reviewed': reviewed,
            'qa_items_reviewed_and_saved': len(cleared_qa),
            'legacy_gaps_reviewed': len(legacy_pending[:25]),
            'kb_items_added': enriched,
            'unresolved_gaps': len(new_unresolved),
            'failed': failed,
            'details': details[:40],
            'scope': 'knowledge_base_only',
            'message': f'Internet God reviewed {reviewed} Q&A turns and added {enriched} KB items.'
        }
        with lock:
            state['last_internet_review'] = review; state['kb_last_enrichment'] = review; state['kb_item_count'] = len(load_kb_items()); state['connectivity_mode'] = CONNECTIVITY_MODE; state['internet_session_active'] = False; state['internet_status_label'] = 'Internet unavailable / offline by default'; save_state()
        log_event('internet_god_qa_review', review['message'], qa_reviewed=reviewed, enriched=enriched, failed=failed, source=source)
        queue_system_speech(f'Internet God reviewed {reviewed} saved answers and added {enriched} knowledge base updates.')
        return review
    except Exception as e:
        review = {'ok': False, 'source': source, 'error': str(e), 'scope': 'knowledge_base_only'}
        with lock:
            state['last_internet_review'] = review; state['last_error'] = str(e); state['internet_session_active'] = False; state['internet_status_label'] = 'Internet unavailable / offline by default'; state['connectivity_mode'] = CONNECTIVITY_MODE; save_state()
        log_event('internet_review_error', str(e), source=source)
        return review

def run_system_judge(text):
    if not (SYSTEM_JUDGE_ENABLED and SYSTEM_JUDGE_API_KEY):
        return {'route': 'qwen', 'enabled': False, 'reason': 'judge disabled or missing api key', 'spoken_status': ''}
    if not system_judge_internet_available():
        verdict = {'route': 'qwen', 'enabled': False, 'skipped': True, 'reason': 'internet unavailable; skipped system judge', 'spoken_status': ''}
        with lock:
            state['last_system_judge'] = verdict
            state['system_judge_enabled'] = SYSTEM_JUDGE_ENABLED
            save_state()
        log_event('system_judge_skipped', 'internet unavailable; using local Qwen')
        return verdict
    user_text = (text or '').strip()[:SYSTEM_JUDGE_MAX_CHARS]
    payload = {
        'model': SYSTEM_JUDGE_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_JUDGE_PROMPT},
            {'role': 'user', 'content': user_text}
        ],
        'max_tokens': 180,
        'temperature': 0,
        'response_format': {'type': 'json_object'}
    }
    try:
        obj = openrouter_post(payload)
        msg = (((obj.get('choices') or [{}])[0]).get('message') or {}).get('content') or ''
        verdict = extract_json_object(msg)
        route = (verdict.get('route') or 'qwen').strip().lower()
        if route not in ('qwen', 'self_improve'):
            route = 'qwen'
        try:
            confidence = float(verdict.get('confidence', 0) or 0)
        except Exception:
            confidence = 0.0
        # Guardrail: ordinary text generation / exact wording requests are a core local Qwen capability, not a missing capability.
        exact_text_request = bool(re.search(r'\b(reply|respond|say|answer)\b.{0,80}\b(exactly|only|just)\b', user_text.lower()))
        if route == 'self_improve' and exact_text_request:
            verdict['original_route'] = 'self_improve'
            verdict['demoted_reason'] = 'exact text generation is handled by local Qwen'
            verdict['local_plan'] = 'Forward to local Qwen for exact text generation; no internet or new capability required.'
            verdict['improvement_request'] = ''
            route = 'qwen'
        if route == 'self_improve' and confidence < SYSTEM_JUDGE_SELF_IMPROVE_MIN_CONFIDENCE:
            # Demote only vague self-improve guesses. Obvious capability gaps must not fall through to Qwen for a useless refusal.
            req_txt = (verdict.get('improvement_request') or '').strip()
            status_txt = (verdict.get('spoken_status') or '').strip().lower()
            reason_txt = (verdict.get('reason') or '').strip().lower()
            concrete = len(req_txt) >= 80 and ('next time' in req_txt.lower() or 'acceptance' in req_txt.lower() or 'should' in req_txt.lower())
            obvious_gap = status_txt.startswith('improving:') or 'cannot' in reason_txt or 'lacks' in reason_txt or 'missing' in reason_txt
            if not req_txt and obvious_gap:
                req_txt = (f"Add the missing capability needed for this user request: {user_text!r}. "
                           f"Reason from system judge: {verdict.get('reason','')}. "
                           f"Update /workspace/voice-ai/voice_daemon.py and related UI/config files if needed. "
                           f"Next time the user says {user_text!r}, the assistant should fulfill the request using local Qwen/tools instead of giving a generic refusal.")
                verdict['improvement_request'] = req_txt
                concrete = True
            if not (concrete or obvious_gap):
                verdict['original_route'] = 'self_improve'
                verdict['demoted_reason'] = 'low confidence and no concrete capability gap; trying local Qwen first'
                route = 'qwen'
                verdict['improvement_request'] = ''
        verdict['route'] = route
        verdict['model'] = SYSTEM_JUDGE_MODEL
        verdict['enabled'] = True
        verdict['raw_content'] = msg[:500]
        with lock:
            state['last_system_judge'] = verdict
            state['system_judge_enabled'] = SYSTEM_JUDGE_ENABLED
            state['system_judge_model'] = SYSTEM_JUDGE_MODEL
            save_state()
        log_event('system_judge', verdict.get('reason',''), route=route, confidence=verdict.get('confidence'), model=SYSTEM_JUDGE_MODEL)
        return verdict
    except Exception as e:
        verdict = {'route': 'qwen', 'enabled': False, 'skipped': True, 'error': str(e), 'reason': 'judge failed open to local Qwen', 'spoken_status': ''}
        with lock:
            state['last_system_judge'] = verdict
            save_state()
        log_event('system_judge_error', str(e))
        return verdict

def apply_system_judge(text):
    verdict = run_system_judge(text)
    route = verdict.get('route') or 'qwen'
    spoken = ''
    audio_spoken = False
    # Audio policy: the judge stays silent for normal local/Qwen routes. The only
    # time the system/judge voice speaks is when it is creating a concrete
    # self-improvement request, so fulfillable requests go straight to Qwen.
    if route == 'self_improve':
        spoken = (verdict.get('spoken_status') or '').strip()
        if not spoken:
            req = (verdict.get('improvement_request') or text or '').strip()
            spoken = 'Improving: ' + req[:90]
        spoken = ' '.join(spoken.split())[:140]
        if SYSTEM_JUDGE_ENABLED and verdict.get('enabled') and spoken:
            queue_system_speech(spoken)
            audio_spoken = True
    else:
        # Keep detailed judge state for the dashboard, but do not speak it.
        verdict['spoken_status'] = ''
        if not verdict.get('local_plan'):
            reason = (verdict.get('reason') or '').strip()
            verdict['local_plan'] = reason or 'Forward to local Qwen and available local/offline tools.'
    verdict['judge_audio_spoken'] = audio_spoken
    verdict['audio_policy'] = 'silent_for_qwen_routes; speak_only_for_self_improve'
    with lock:
        state['last_system_judge'] = verdict
        save_state()
    return verdict



def looks_like_exact_response_request(text):
    t = (text or '').lower()
    return any(m in t for m in ['reply with exactly', 'answer exactly', 'say exactly', 'respond with exactly', 'repeat exactly'])

def spoken_max_tokens_for(text):
    t = (text or '').lower()
    detailed_markers = [
        'explain in detail', 'detailed', 'step by step', 'step-by-step',
        'long answer', 'full explanation', 'tell me everything', 'essay',
        'list all', 'compare and contrast', 'why exactly'
    ]
    if any(m in t for m in detailed_markers):
        return min(QWEN_MAX_TOKENS, 700)
    return min(QWEN_MAX_TOKENS, int(os.environ.get('VOICE_QWEN_SPOKEN_DEFAULT_MAX_TOKENS', '160')))


def polish_spoken_response(user_text, response):
    response = (response or '').strip()
    if not response or looks_like_exact_response_request(user_text):
        return response
    words = response.split()
    sentence_count = sum(response.count(x) for x in '.!?')
    wants_detail = spoken_max_tokens_for(user_text) > 200
    if wants_detail or (len(words) <= 35 and sentence_count <= 3 and '\n' not in response and '-' not in response[:20]):
        return response
    try:
        payload = {
            'model': 'qwen-voice-local',
            'messages': [
                {'role': 'system', 'content': 'Rewrite the answer for text-to-speech. Keep the same meaning, but make it natural spoken English. Maximum 30 words. One or two short sentences. No markdown. No preamble.'},
                {'role': 'user', 'content': 'Question: ' + (user_text or '') + '\n\nAnswer to rewrite: ' + response}
            ],
            'max_tokens': 80,
            'temperature': 0.1,
            'stream': False,
            'chat_template_kwargs': {'enable_thinking': False}
        }
        obj = qwen_post(payload, timeout=120)
        msg = ((obj.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        polished = msg.strip().strip('"')
        if polished and len(polished.split()) <= max(45, len(words)):
            log_event('spoken_polish', 'shortened response for speech', before_words=len(words), after_words=len(polished.split()))
            return polished
    except Exception as e:
        log_event('spoken_polish_error', str(e)[:500])
    return response

def ask_qwen(text):
    # Deterministic local routes run before the external judge so obvious built-in
    # capabilities don't get misrouted or delayed by internet/model judgment.
    if SELF_IMPROVE_ENABLED and looks_like_self_improve_request(text):
        return handle_self_improve_direct(text)
    if TOOL_CALLING_ENABLED and looks_like_ping_request(text):
        return handle_ping_direct(text)
    if TOOL_CALLING_ENABLED and looks_like_weather_request(text):
        return handle_weather_direct(text)
    # New offline-first education flow: ordinary questions do NOT go to the
    # external Internet God/system judge. The Local Jetson Tutor answers first
    # with local model/tools/KB; answer-quality grading later saves weak answers
    # to the KB queue. Internet God only speaks/runs when the user presses
    # Connect to Internet / Enrich KB, or for explicit non-education self-improve.
    judge = {
        'route': 'qwen',
        'enabled': False,
        'skipped': True,
        'agent': 'Local Jetson Tutor',
        'reason': 'Internet is off by default; Local Jetson Tutor answers first.',
        'local_plan': 'Use the local Jetson model, local tools, and local KB. If the answer is weak, save the question to the KB enrichment queue.',
        'spoken_status': '',
        'judge_audio_spoken': False,
        'audio_policy': 'Internet God is silent until Connect to Internet + Enrich KB.'
    }
    with lock:
        state['last_system_judge'] = judge
        save_state()
    history_messages = trim_history(load_history())
    kb_context = load_kb_context(text)
    # KB must be allowed to change the answer. If relevant KB exists, do not pass
    # prior chat history, because old Q&A turns can make the model repeat a stale
    # pre-enrichment answer. If no KB exists, filter near-duplicate prior turns so
    # deleting a KB item can also change the answer to the same question.
    if kb_context:
        history_messages = []
    else:
        cur_terms = set(simple_terms(text))
        filtered = []
        for hm in history_messages:
            terms = set(simple_terms(hm.get('content','')))
            overlap = len(cur_terms & terms)
            denom = max(1, min(len(cur_terms), len(terms)))
            if overlap / denom >= 0.75:
                continue
            filtered.append(hm)
        history_messages = filtered
    system_prompt = VOICE_SYSTEM_PROMPT
    if kb_context:
        system_prompt += '\n\nAUTHORITATIVE LOCAL ENRICHED KNOWLEDGE BASE NOTES FOR THIS QUESTION:\n' + kb_context + '\n\nKB RULES: The notes above were added by Internet God after reviewing earlier answers. For this turn, they are newer and more important than your base model memory and chat history. Your answer MUST use the KB teacher correction first, before base-model memory. Do not repeat the previous weak answer. Keep it spoken and concise, but make the answer visibly improved by including the correction or missing fact from the KB.'
    else:
        system_prompt += '\n\nNo relevant enriched local KB note matched this question. Answer from the local model only. Do not copy a previous answer to the same question from memory/history; give the best fresh local answer.'
    messages = [{'role':'system','content': system_prompt}] + history_messages + [
        {'role':'user','content': text}
    ]
    forced_tool_used = append_forced_tool_use(messages, text)
    raw_rounds = []
    response = ''
    max_rounds = 4 if TOOL_CALLING_ENABLED else 1
    for round_i in range(max_rounds):
        payload = {
            'model': 'qwen-voice-local',
            'messages': messages,
            'max_tokens': spoken_max_tokens_for(text),
            'temperature': 0.15 if TOOL_CALLING_ENABLED else 0.45,
            'stream': False,
            'chat_template_kwargs': {'enable_thinking': False}
        }
        if TOOL_CALLING_ENABLED:
            payload['tools'] = active_tool_specs()
            payload['tool_choice'] = 'auto'
        obj = qwen_post(payload, timeout=300)
        raw_rounds.append(obj)
        choice = (obj.get('choices') or [{}])[0]
        msg = choice.get('message') or {}
        tool_calls = msg.get('tool_calls') or []
        if tool_calls:
            messages.append({'role': 'assistant', 'content': msg.get('content') or '', 'tool_calls': tool_calls})
            for tc in tool_calls:
                fn = (tc.get('function') or {})
                name = fn.get('name') or ''
                args = fn.get('arguments') or '{}'
                tool_call_id = tc.get('id') or f'toolcall-{round_i}'
                if name == 'note_tool_use':
                    result = run_note_tool_use(args)
                elif name == 'run_python_code':
                    result = run_python_tool(args)
                elif name == 'run_shell_command':
                    result = run_shell_tool(args)
                elif name == 'self_improve':
                    result = run_self_improve_tool(args)
                else:
                    result = json.dumps({'ok': False, 'error': f'Unknown tool {name}'})
                messages.append({'role': 'tool', 'tool_call_id': tool_call_id, 'name': name, 'content': result})
            continue
        response = (msg.get('content') or '').strip()
        break
    if not response:
        response = 'I ran the tool, but I could not produce a final answer.'
    response = response if kb_context else polish_spoken_response(text, response)
    with lock:
        state['partial_response'] = response
        state['last_response'] = response
        save_state()
    speak_final_response(response)
    append_history_turn(text, response)
    quality = record_qa_for_internet_review(text, response, {'system_judge': judge, 'rounds': len(raw_rounds)})
    return response, {'tool_calling': TOOL_CALLING_ENABLED, 'system_judge': judge, 'answer_quality': quality, 'force_tool_each_turn': FORCE_TOOL_EACH_TURN, 'forced_tool_used': forced_tool_used, 'rounds': len(raw_rounds), 'history_messages': len(history_messages), 'kb_context_used': bool(kb_context), 'kb_context_count': state.get('last_kb_context_count', 0), 'kb_context_items': state.get('last_kb_context_items', [])}

def live_transcribe_loop(session_id, path):
    # Periodically transcribe a snapshot of the growing WAV while the button is still held/recording.
    next_time = time.time() + LIVE_TRANSCRIBE_INTERVAL
    last_text = ''
    while True:
        time.sleep(max(0.2, next_time - time.time()))
        next_time = time.time() + LIVE_TRANSCRIBE_INTERVAL
        with lock:
            active = (record_session == session_id and record_path == path and record_proc and record_proc.poll() is None)
        if not active:
            return
        try:
            if not os.path.exists(path) or os.path.getsize(path) < 64000:
                continue
            snap = os.path.join(AUDIO_DIR, f'live-partial-{session_id}.wav')
            subprocess.run(['cp', path, snap], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            if not os.path.exists(snap) or os.path.getsize(snap) < 64000:
                continue
            cmd = [WHISPER, '-m', WHISPER_MODEL, '-f', snap, '-nt', '-np', '-l', 'en', '-t', '2']
            p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            if p.returncode != 0:
                log_event('partial_transcript_error', p.stderr[-500:])
                continue
            lines = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
            text = ' '.join(lines).strip()
            if text in ('[BLANK_AUDIO]', '[inaudible]') or text.lower() in ('[blank_audio]', '[inaudible]'):
                text = ''
            if text and text != last_text:
                last_text = text
                with lock:
                    state['partial_transcript'] = text
                    state['last_transcript'] = text
                    save_state()
                log_event('partial_transcript', text, audio_file=path)
        except Exception as e:
            log_event('partial_transcript_error', str(e))

def process_text(transcript, source='text'):
    try:
        transcript = (transcript or '').strip()
        if not transcript:
            set_status('idle', last_error='Blank text command')
            return
        if not should_process_user_input(transcript, source=source):
            return
        set_status('thinking', last_transcript=transcript, last_response='', partial_response='', speaking_text='', last_tool_name='', last_tool_result='', last_answer_quality={'enabled': False, 'source': 'internet_god_deferred', 'reason': 'Waiting for Local Jetson Tutor answer; Internet God reviews later.'}, last_system_judge={}, max_output_tokens=QWEN_MAX_TOKENS)
        log_event('thinking', 'Sending text to Qwen', source=source, text=transcript[:300])
        response, raw = ask_qwen(transcript)
        set_status('idle', last_response=response, partial_response=response, max_output_tokens=QWEN_MAX_TOKENS)
        log_event('response', response or '(empty)', source=source)
    except Exception as e:
        set_status('error', last_error=str(e))
        log_event('error', str(e), source=source)

def process_audio(path):
    try:
        if not path or not os.path.exists(path) or os.path.getsize(path) < 2048:
            set_status('idle', last_error='No usable audio captured')
            log_event('error', 'No usable audio captured', audio_file=path or '')
            return
        live_partial = (state.get('partial_transcript') or '').strip()
        if live_partial and USE_PARTIAL_ON_STOP:
            transcript = live_partial
            set_status('thinking', last_transcript=transcript, partial_transcript=transcript, last_response='', partial_response='', speaking_text='', last_tool_name='', last_tool_result='', last_answer_quality={'enabled': False, 'source': 'internet_god_deferred', 'reason': 'Waiting for Local Jetson Tutor answer; Internet God reviews later.'}, last_system_judge={}, max_output_tokens=QWEN_MAX_TOKENS)
            log_event('transcript', transcript, audio_file=path, source='live_partial_used')
        else:
            set_status('transcribing')
            log_event('transcribing', 'Transcribing with whisper.cpp base.en', audio_file=path)
            transcript = transcribe(path)
            set_status('thinking', last_transcript=transcript, partial_transcript=transcript, last_response='', partial_response='', speaking_text='', last_tool_name='', last_tool_result='', last_answer_quality={'enabled': False, 'source': 'internet_god_deferred', 'reason': 'Waiting for Local Jetson Tutor answer; Internet God reviews later.'}, last_system_judge={}, max_output_tokens=QWEN_MAX_TOKENS)
            log_event('transcript', transcript or '(blank)', audio_file=path)
        if not transcript:
            set_status('idle', last_error='Blank audio / no speech detected')
            return
        if not should_process_user_input(transcript, source='voice', audio_file=path):
            return
        log_event('thinking', 'Sending transcript to Qwen')
        response, raw = ask_qwen(transcript)
        set_status('idle', last_response=response, partial_response=response, max_output_tokens=QWEN_MAX_TOKENS)
        log_event('response', response or '(empty)')
    except Exception as e:
        set_status('error', last_error=str(e))
        log_event('error', str(e))

def handle_command(cmd, source='command'):
    action = (cmd.get('action') or '').lower()
    if action == 'start': start_recording(source)
    elif action == 'stop': stop_recording(source)
    elif action == 'ask': threading.Thread(target=process_text, args=(cmd.get('text') or '', source), daemon=True).start()
    elif action == 'say': queue_speech(cmd.get('text') or '', voice=cmd.get('voice') or 'assistant')
    elif action in ('connect_internet', 'review_weak_answers'): threading.Thread(target=process_weak_answer_backlog, args=(source,), daemon=True).start()
    elif action == 'status': save_state(); update_weak_answer_state()
    else: log_event('ignored', f'Unknown command: {action}', source=source)

def recording_watchdog_loop():
    while True:
        time.sleep(1.0)
        try:
            with lock:
                if state.get('status') == 'recording':
                    if (not record_proc) or (record_proc.poll() is not None):
                        recover_stale_recording_locked('watchdog saw no active recorder', source='watchdog')
                    elif record_started:
                        state['recording_seconds'] = round(time.time() - record_started, 1)
                        save_state()
        except Exception as e:
            log_event('recording_watchdog_error', str(e))

def command_loop():
    open(COMMANDS, 'a').close()
    pos = os.path.getsize(COMMANDS)
    while True:
        try:
            with open(COMMANDS, 'r') as f:
                f.seek(pos)
                while True:
                    line = f.readline()
                    if not line:
                        break
                    pos = f.tell()
                    try:
                        handle_command(json.loads(line), 'ui')
                    except Exception as e:
                        log_event('error', f'Bad command: {e}')
        except Exception as e:
            log_event('error', f'Command loop error: {e}')
        time.sleep(0.25)

def key_loop():
    fds = {}
    path_to_fd = {}

    def rescan():
        devices = discover_event_devices()
        opened = 0
        for d in devices:
            path = d['path']
            # Only real keyboard/consumer-control devices can carry volume keys.
            if 'kbd' not in d.get('handlers',''):
                continue
            if path in path_to_fd and path_to_fd[path] in fds:
                continue
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                fds[fd] = d
                path_to_fd[path] = fd
                opened += 1
            except Exception as e:
                # Hotplug races are normal; try again next scan.
                pass
        with lock:
            state['event_devices'] = devices
            save_state()
        return opened, devices

    opened, devices = rescan()
    log_event('ready', f'Listening for volume keys on {len(fds)} input devices', devices=devices)
    EVENT_SIZE = struct.calcsize('llHHI')
    last_rescan = 0
    while True:
        now_ts = time.time()
        if now_ts - last_rescan > 5:
            before = len(fds)
            opened, devices = rescan()
            if opened:
                log_event('hotplug', f'Reopened {opened} input device(s); now listening on {len(fds)}', devices=devices)
            last_rescan = now_ts
        if not fds:
            time.sleep(0.5)
            continue
        r, _, _ = select.select(list(fds.keys()), [], [], 0.5)
        for fd in r:
            try:
                data = os.read(fd, 4096)
            except BlockingIOError:
                continue
            except OSError as e:
                dev = fds.get(fd, {})
                log_event('hotplug', f'Input device disappeared; will rescan: {dev}: {e}')
                try: os.close(fd)
                except Exception: pass
                fds.pop(fd, None)
                if dev.get('path') in path_to_fd:
                    path_to_fd.pop(dev.get('path'), None)
                continue
            for off in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
                tv_sec, tv_usec, ev_type, code, value = struct.unpack('llHHI', data[off:off+EVENT_SIZE])
                if ev_type == 1 and value == 1 and code in (114, 115):
                    dev = fds[fd]
                    if code == 115:
                        log_event('key', 'Volume Up pressed: start listening', device=dev)
                        start_recording('volume_up')
                    elif code == 114:
                        log_event('key', 'Volume Down pressed: stop listening', device=dev)
                        stop_recording('volume_down')
        do_timeout = False
        with lock:
            if record_proc and record_proc.poll() is None and record_started:
                elapsed = time.time() - record_started
                state['recording_seconds'] = round(elapsed, 1)
                save_state()
                if elapsed > MAX_RECORD_SECONDS:
                    do_timeout = True
        if do_timeout:
            log_event('timeout', 'Max recording time reached; stopping automatically')
            stop_recording('timeout')


def reset_transient_state_on_startup():
    # After a crash/restart, never leave the UI stuck in recording/transcribing/thinking.
    with lock:
        if state.get('status') in ('recording','transcribing','thinking','responding','speaking','error'):
            state['status'] = 'idle'
        state['recording_seconds'] = 0
        state['recording_file'] = None
        state['partial_transcript'] = ''
        state['partial_response'] = ''
        state['speaking'] = False
        state['speaking_text'] = ''
        state['last_error'] = ''
        save_state()

def cleanup_orphan_arecord_processes():
    # Daemon restarts can leave an old arecord holding the mic; clear only our recording jobs.
    try:
        res = subprocess.run(['pgrep', '-af', '^arecord .* /workspace/voice-ai/recordings/'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=3)
        killed = []
        for line in (res.stdout or '').splitlines():
            parts = line.split(None, 1)
            if parts and parts[0].isdigit():
                try:
                    os.kill(int(parts[0]), signal.SIGTERM)
                    killed.append(int(parts[0]))
                except Exception:
                    pass
        if killed:
            time.sleep(0.4)
            for pid in killed:
                try: os.kill(pid, signal.SIGKILL)
                except Exception: pass
            log_event('recording_recovered', 'Killed orphan arecord process(es) from previous daemon run', pids=killed)
    except Exception as e:
        log_event('recording_recovery_error', str(e))

def main():
    cleanup_orphan_arecord_processes()
    reset_transient_state_on_startup()
    update_weak_answer_state()
    update_qa_review_state()
    with lock:
        state['kb_item_count'] = len(load_kb_items())
        save_state()
    set_status('idle')
    threading.Thread(target=tts_worker, daemon=True).start()
    threading.Thread(target=command_loop, daemon=True).start()
    threading.Thread(target=recording_watchdog_loop, daemon=True).start()
    key_loop()

if __name__ == '__main__':
    main()

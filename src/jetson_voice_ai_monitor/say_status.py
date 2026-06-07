#!/usr/bin/env python3
import json, sys, pathlib, os

def main():
    msg = ' '.join(sys.argv[1:]).strip()
    if not msg:
        print('usage: jetson-voice-say "status text"', file=sys.stderr)
        return 2
    path = pathlib.Path(os.environ.get('VOICE_AI_BASE', '/workspace/voice-ai')) / 'commands.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps({'action':'say','text':msg}) + '\n')
    print('queued:', msg)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

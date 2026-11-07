#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot local CODOL server connection test.

Starts the local GDP/TQoS server, launches the game with host redirection,
waits, and reports every packet/connection the client made to the local
stand-in. This is the first end-to-end local server contract test.
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
GAME = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
                    'codoMP_client_shipRetail.exe')
CWD = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe', 'CrossProxy.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, 'CODOLServer', '_localconn')
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    os.makedirs(out, exist_ok=True)
    kill_tree()

    server = subprocess.Popen(
        [sys.executable, '-X', 'utf8', '-u',
         os.path.join(HERE, 'gdp_server.py'),
         '--out', out, '--ports', '8000,8081,3074,10009,10010,443',
         '--seconds', str(seconds + 20)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    harness = subprocess.Popen(
        [sys.executable, '-X', 'utf8', '-u',
         os.path.join(HERE, 'suspend_host_redirect.py'),
         '--exe', GAME, '--cwd', CWD,
         '--out', os.path.join(out, 'harness'),
         '--no-listeners', '--seconds', str(seconds),
         '--reply-variant', '3'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    time.sleep(seconds)
    for p in (harness, server):
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(2)
    kill_tree()

    # Summarize the server trace.
    trace = os.path.join(out, 'gdp_server.jsonl')
    events = []
    if os.path.isfile(trace):
        for line in open(trace, encoding='utf-8', errors='replace'):
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    payloads = [e for e in events if e.get('len')]
    summary = {
        'out': out,
        'events': len(events),
        'payloads': len(payloads),
        'ports': sorted(set(e.get('port') for e in payloads)),
        'tqos_requests': sum(1 for e in payloads if e.get('data_hex', '').startswith('7572')),
        'gdp_candidates': sum(1 for e in payloads
                              if not e.get('data_hex', '').startswith('7572')),
    }
    with open(os.path.join(out, 'LOCAL_CONNECTION_RESULT.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

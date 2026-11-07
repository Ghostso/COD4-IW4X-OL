#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Advertise the local GameSvr on different ports and record client reactions."""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RUNS = os.path.join(ROOT, 'run_codol_001', 'runs')
GAME = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
                    'codoMP_client_shipRetail.exe')
CWD = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')
PORTS = [443, 3074, 8000, 10009, 10010, 28960, 20810]


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def load(path):
    rows = []
    if os.path.isfile(path):
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def run_port(port, seconds=45):
    out = os.path.join(RUNS, 'PORT_SWEEP_%d' % port)
    os.makedirs(out, exist_ok=True)
    kill_tree()
    argv = [sys.executable, '-X', 'utf8', '-u',
            os.path.join(HERE, 'suspend_host_redirect.py'),
            '--exe', GAME, '--cwd', CWD, '--out', out,
            '--seconds', str(seconds), '--reply-variant', '4',
            '--advertise-port', str(port)]
    with open(os.path.join(out, 'attempt_stdout.txt'), 'w',
              encoding='utf-8', errors='replace') as log:
        try:
            subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                           timeout=seconds + 40)
        except subprocess.TimeoutExpired:
            log.write('\nTIMEOUT\n')
    rows = load(os.path.join(out, 'local_listeners.jsonl'))
    tcp_in = [r for r in rows if r.get('proto') == 'tcp' and r.get('len')]
    udp_in = [r for r in rows if r.get('proto') == 'udp' and r.get('len')]
    tqos = [r for r in rows if r.get('sent_reply_len')]
    return {'port': port, 'dir': out, 'tqos_reply': len(tqos),
            'tcp_in': len(tcp_in), 'udp_in': len(udp_in),
            'tcp_ports': sorted(set(r['port'] for r in tcp_in)),
            'udp_ports': sorted(set(r['port'] for r in udp_in))}


def main():
    results = []
    for p in PORTS:
        r = run_port(p)
        results.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        kill_tree()
    out = os.path.join(RUNS, 'PORT_SWEEP_SUMMARY.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print('SUMMARY=' + out, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

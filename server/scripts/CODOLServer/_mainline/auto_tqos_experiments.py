#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_tqos_experiments.py -- unattended TQoS response experiment matrix.

For each response variant, repeatedly launches the local fake stack until the
client actually emits a 'ur' request, then records whether the variant produced
follow-on network activity. Writes a JSON summary and per-attempt directories.

Run elevated (usually through elevated_agent.py).
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RUN_ROOT = os.path.join(ROOT, 'run_codol_001', 'runs')
GAME = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
                    'codoMP_client_shipRetail.exe')
CWD = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def read_jsonl(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def run_attempt(variant, attempt, seconds):
    out = os.path.join(RUN_ROOT, 'AUTO_TQOS_V%d_A%d' % (variant, attempt))
    os.makedirs(out, exist_ok=True)
    kill_tree()
    argv = [sys.executable, '-X', 'utf8', '-u',
            os.path.join(HERE, 'run_fake_stack.py'),
            '--exe', GAME, '--cwd', CWD, '--out', out,
            '--seconds', str(seconds), '--reply',
            '--variant', str(variant)]
    with open(os.path.join(out, 'attempt_stdout.txt'), 'w',
              encoding='utf-8', errors='replace') as log:
        try:
            subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                           timeout=seconds + 45)
        except subprocess.TimeoutExpired:
            log.write('\nTIMEOUT\n')
    trace = read_jsonl(os.path.join(out, 'server', 'fake_tqos.jsonl'))
    got_ur = any(r.get('parsed', {}).get('magic') == 'ur' for r in trace)
    tcp = [r for r in trace if r.get('proto') == 'tcp' and r.get('len')]
    return {
        'variant': variant,
        'attempt': attempt,
        'dir': out,
        'got_ur': got_ur,
        'records': len(trace),
        'tcp_requests': len(tcp),
    }


def main():
    variants = [0, 1, 2, 3, 4, 5]
    seconds = 35
    results = []
    for v in variants:
        for a in range(1, 4):
            r = run_attempt(v, a, seconds)
            results.append(r)
            print(json.dumps(r, ensure_ascii=False), flush=True)
            if r['got_ur']:
                break
            kill_tree()
    summary = os.path.join(RUN_ROOT, 'AUTO_TQOS_SUMMARY.json')
    with open(summary, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print('SUMMARY=' + summary, flush=True)
    kill_tree()
    return 0


if __name__ == '__main__':
    sys.exit(main())

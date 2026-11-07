#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qos8081_matrix.py -- unattended reply experiment matrix for the 8081 QoS
channel.

For each reply mode it launches the harness, waits for 8081 traffic, replies
with that mode, and records whether the client shows any follow-on behaviour
(more 8081 packets, new ports, TCP attempts, or process staying alive longer).

Writes per-mode run dirs plus a summary JSON.
"""

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

MODES = ['none', 'echo', 'echotail', 'zero84', 'zerosame']


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


def run_mode(mode, seconds=75, attempts=4):
    for attempt in range(1, attempts + 1):
        out = os.path.join(RUNS, 'QOS8081_%s_A%d' % (mode, attempt))
        os.makedirs(out, exist_ok=True)
        kill_tree()
        argv = [sys.executable, '-X', 'utf8', '-u',
                os.path.join(HERE, 'suspend_host_redirect.py'),
                '--exe', GAME, '--cwd', CWD, '--out', out,
                '--seconds', str(seconds), '--reply-variant', '3']
        if mode != 'none':
            argv += ['--qos-mode', mode]
        with open(os.path.join(out, 'attempt_stdout.txt'), 'w',
                  encoding='utf-8', errors='replace') as log:
            try:
                subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                               timeout=seconds + 40)
            except subprocess.TimeoutExpired:
                log.write('\nTIMEOUT\n')
        rows = load(os.path.join(out, 'local_listeners.jsonl'))
        p8081 = [r for r in rows if r.get('proto') == 'udp' and r.get('port') == 8081 and r.get('len')]
        replies = [r for r in rows if r.get('sent_qos_len')]
        tcp_in = [r for r in rows if r.get('proto') == 'tcp' and r.get('len')]
        res = {'mode': mode, 'attempt': attempt, 'dir': out,
               'packets_8081': len(p8081), 'qos_replies': len(replies),
               'tcp_in': len(tcp_in),
               'len_hist': sorted(set(r['len'] for r in p8081))}
        print(json.dumps(res, ensure_ascii=False), flush=True)
        if p8081:
            return res
        kill_tree()
    return {'mode': mode, 'attempt': attempts, 'no_8081': True}


def main():
    results = []
    for m in MODES:
        r = run_mode(m)
        results.append(r)
        kill_tree()
    summary = os.path.join(RUNS, 'QOS8081_MATRIX_SUMMARY.json')
    with open(summary, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print('SUMMARY=' + summary, flush=True)
    kill_tree()
    return 0


if __name__ == '__main__':
    sys.exit(main())

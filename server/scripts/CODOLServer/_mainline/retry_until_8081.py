#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retry_until_8081.py -- retry the variant-3 harness until the client actually
enters the 8081 QoS measurement stage, then archive that run.

Unattended: it loops launch/observe/cleanup, keeps every attempt, and copies the
first run that produced 8081 traffic into a stable folder.
"""

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RUNS = os.path.join(ROOT, 'run_codol_001', 'runs')
GAME = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
                    'codoMP_client_shipRetail.exe')
CWD = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')
ARCHIVE = os.path.join(RUNS, 'BEST_8081_STAGE')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def count_8081(path):
    if not os.path.isfile(path):
        return 0
    n = 0
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get('proto') == 'udp' and row.get('port') == 8081 and row.get('len'):
                n += 1
    return n


def main():
    max_attempts = 12
    seconds = 40
    results = []
    for attempt in range(1, max_attempts + 1):
        out = os.path.join(RUNS, 'RETRY_V3_A%02d' % attempt)
        os.makedirs(out, exist_ok=True)
        kill_tree()
        argv = [sys.executable, '-X', 'utf8', '-u',
                os.path.join(HERE, 'suspend_host_redirect.py'),
                '--exe', GAME, '--cwd', CWD, '--out', out,
                '--seconds', str(seconds), '--reply-variant', '3']
        with open(os.path.join(out, 'attempt_stdout.txt'), 'w',
                  encoding='utf-8', errors='replace') as log:
            try:
                subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                               timeout=seconds + 40)
            except subprocess.TimeoutExpired:
                log.write('\nTIMEOUT\n')
        n = count_8081(os.path.join(out, 'local_listeners.jsonl'))
        results.append({'attempt': attempt, 'dir': out, 'packets_8081': n})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
        if n > 0:
            if os.path.isdir(ARCHIVE):
                shutil.rmtree(ARCHIVE, ignore_errors=True)
            shutil.copytree(out, ARCHIVE)
            print('ARCHIVED=' + ARCHIVE, flush=True)
            break
    summary = os.path.join(RUNS, 'RETRY_V3_SUMMARY.json')
    with open(summary, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print('SUMMARY=' + summary, flush=True)
    kill_tree()
    return 0


if __name__ == '__main__':
    sys.exit(main())

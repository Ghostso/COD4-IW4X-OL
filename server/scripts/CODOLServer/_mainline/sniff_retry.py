#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sniff_retry.py -- retry the key sniff until a run captures 8081 traffic.

The 8081 QoS channel only appears in some launches, so this loops short runs
and keeps the first result that actually produced 8081 packets plus a key
candidate that decrypts them.
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
ARCHIVE = os.path.join(ROOT, 'CODOLServer', 'KEY_FOUND_RUN')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def count_8081(path):
    n = 0
    if not os.path.isfile(path):
        return 0
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get('port') == 8081 and o.get('data_hex'):
                n += 1
    return n


def main():
    attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    variant = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    results = []
    for a in range(1, attempts + 1):
        out = os.path.join(ROOT, 'CODOLServer', '_sniff_A%02d' % a)
        os.makedirs(out, exist_ok=True)
        kill_tree()
        argv = [sys.executable, '-X', 'utf8', '-u',
                os.path.join(HERE, 'key_string_sniff.py'),
                '--out', out, '--exe', GAME, '--cwd', CWD,
                '--seconds', '75', '--reply-variant', str(variant)]
        with open(os.path.join(out, 'run_stdout.txt'), 'w',
                  encoding='utf-8', errors='replace') as log:
            try:
                subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                               timeout=140)
            except subprocess.TimeoutExpired:
                log.write('\nTIMEOUT\n')
        n = count_8081(os.path.join(out, 'local_listeners.jsonl'))
        found = os.path.isfile(os.path.join(out, 'aes_key_FOUND.json'))
        rec = {'attempt': a, 'variant': variant, 'packets_8081': n,
               'key_found': found, 'dir': out}
        results.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        if n > 0 or found:
            if os.path.isdir(ARCHIVE):
                shutil.rmtree(ARCHIVE, ignore_errors=True)
            shutil.copytree(out, ARCHIVE)
            print('ARCHIVED=' + ARCHIVE, flush=True)
            if found:
                break
    out = os.path.join(ROOT, 'CODOLServer', '_sniff_summary.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print('SUMMARY=' + out, flush=True)
    kill_tree()
    return 0


if __name__ == '__main__':
    sys.exit(main())

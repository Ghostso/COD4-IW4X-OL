#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retry live_platform_key until the 8081 stage is reached and a key matches."""

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ARCHIVE = os.path.join(ROOT, 'CODOLServer', 'KEY_FOUND_PLATFORM')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe', 'CrossProxy.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def main():
    attempts = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    results = []
    for a in range(1, attempts + 1):
        out = os.path.join(ROOT, 'CODOLServer', '_liveplat_A%02d' % a)
        os.makedirs(out, exist_ok=True)
        kill_tree()
        argv = [sys.executable, '-X', 'utf8', '-u',
                os.path.join(HERE, 'live_platform_key.py'),
                '--out', out, '--seconds', '200']
        with open(os.path.join(out, 'run_stdout.txt'), 'w',
                  encoding='utf-8', errors='replace') as log:
            try:
                subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                               timeout=420)
            except subprocess.TimeoutExpired:
                log.write('\nTIMEOUT\n')
        found = os.path.isfile(os.path.join(out, 'aes_key_FOUND.json'))
        n8081 = 0
        hp = os.path.join(out, 'harness', 'local_listeners.jsonl')
        if os.path.isfile(hp):
            with open(hp, encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if o.get('port') == 8081 and o.get('data_hex'):
                        n8081 += 1
        rec = {'attempt': a, 'packets_8081': n8081, 'key_found': found,
               'dir': out}
        results.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        if found:
            if os.path.isdir(ARCHIVE):
                shutil.rmtree(ARCHIVE, ignore_errors=True)
            shutil.copytree(out, ARCHIVE)
            print('ARCHIVED=' + ARCHIVE, flush=True)
            break
    out = os.path.join(ROOT, 'CODOLServer', '_liveplat_summary.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print('SUMMARY=' + out, flush=True)
    kill_tree()
    return 0


if __name__ == '__main__':
    sys.exit(main())

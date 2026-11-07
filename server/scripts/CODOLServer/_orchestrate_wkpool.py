#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Attach to codoMP_client_shipRetail.exe the moment it appears and install the
WKNet pool redirect, so the game's first outbound connects go to 127.0.0.1.

Run this FIRST (it waits for the game), then start the game via the solidified
direct launcher.

Usage:
    python _orchestrate_wkpool.py --wait 120 --duration 180
"""

import argparse
import json
import os
import subprocess
import sys
import time

import frida

HERE = os.path.dirname(os.path.abspath(__file__))
PROCESS = 'codoMP_client_shipRetail.exe'


def list_pids(name):
    try:
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq ' + name, '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return []
    pids = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.strip().split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wait', type=float, default=120.0)
    ap.add_argument('--duration', type=float, default=180.0)
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'wkpool_run.jsonl'))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)

    def log(rec):
        line = json.dumps(rec, ensure_ascii=False, default=str)
        print(line, flush=True)
        with open(args.log, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')

    log({'kind': 'orchestrator_ready', 'since': time.time()})
    started = time.time() - 2.0
    injected = set()
    sessions = []

    deadline = time.time() + args.wait
    pid = None
    while time.time() < deadline:
        for cand in list_pids(PROCESS):
            if cand in injected:
                continue
            # only accept a process that started after we did
            try:
                created = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-Command',
                     "(Get-Process -Id %d -ErrorAction Stop).StartTime.Ticks" % cand],
                    capture_output=True, text=True, timeout=8).stdout.strip()
                if created.isdigit():
                    created_ts = int(created) / 1e7 - 11644473600
                    if created_ts < started:
                        injected.add(cand)
                        continue
            except Exception:  # noqa: BLE001
                pass
            pid = cand
            break
        if pid:
            break
        time.sleep(0.05)

    if not pid:
        log({'kind': 'game_not_found'})
        return 2

    log({'kind': 'found', 'pid': pid})
    try:
        session = frida.attach(pid)
        with open(os.path.join(HERE, 'frida_redirect_wkpool.js'), encoding='utf-8') as fh:
            source = fh.read()
        script = session.create_script(source)
        script.on('message', lambda m, d: log(
            dict(m.get('payload'), label='wkpool') if isinstance(m.get('payload'), dict)
            else {'raw': m, 'label': 'wkpool'}))
        script.load()
        sessions.append((session, script))
        log({'kind': 'injected', 'pid': pid})
    except Exception as exc:  # noqa: BLE001
        log({'kind': 'inject_failed', 'pid': pid, 'error': repr(exc)})
        return 1

    log({'kind': 'holding', 'pid': pid, 'duration': args.duration})
    end = time.time() + args.duration
    while time.time() < end:
        time.sleep(0.5)
    for session, script in sessions:
        try:
            script.unload()
        except Exception:  # noqa: BLE001
            pass
        try:
            session.detach()
        except Exception:  # noqa: BLE001
            pass
    log({'kind': 'done'})
    return 0


if __name__ == '__main__':
    sys.exit(main())

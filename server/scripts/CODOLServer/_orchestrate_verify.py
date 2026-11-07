"""Attach-and-inject orchestrator for the CODOL TCLS directory redirect.

Why this exists
---------------
tcls_core issues its directory connect() only ~16 s after launch, and Frida's
spawn gating is unavailable on this host ("not yet supported on this OS").
Attaching after the fact therefore always misses the connect().

Approach
--------
Poll for tcls_core.exe at a very short interval (50 ms) the moment the TGP chain
is started, and attach as soon as the PID exists. tcls_core must first load its
DLLs and initialise Tenio before it can query the directory, which gives us a
window of roughly 10-15 seconds - far more than the attach needs.

Usage
-----
Start this first, then launch TGP:

    python _orchestrate.py --wait 120 --duration 180 --trace
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import time

import frida

HERE = os.path.dirname(os.path.abspath(__file__))
PROCESS_NAME = 'tcls_core.exe'


def list_pids(name):
    """Return PIDs for `name` via tasklist (works for elevated processes too)."""
    try:
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq ' + name, '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return []
    pids = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith('"'):
            continue
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def start_time(pid):
    """Best-effort process start time (unix seconds) using WMI via PowerShell."""
    try:
        out = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command',
             "(Get-Process -Id %d -ErrorAction Stop).StartTime.ToString('o')" % pid],
            capture_output=True, text=True, timeout=10).stdout.strip()
        if out:
            import datetime
            return datetime.datetime.fromisoformat(out).timestamp()
    except Exception:  # noqa: BLE001
        pass
    return None


class Runner:
    def __init__(self, log_path, trace):
        self.log_path = log_path
        self.trace = trace
        self.sessions = []

    def log(self, rec):
        line = json.dumps(rec, ensure_ascii=False, default=str)
        print(line, flush=True)
        if self.log_path:
            with open(self.log_path, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')

    def inject(self, pid):
        scripts = []
        if self.trace:
            scripts.append(('trace', os.path.join(HERE, '_trace_real_path.js')))
        scripts.append(('redirect', os.path.join(HERE, '_verify_rewrite.js')))
        for label, path in scripts:
            try:
                session = frida.attach(pid)
                with open(path, 'r', encoding='utf-8') as fh:
                    source = fh.read()
                script = session.create_script(source)

                def on_message(message, data, label=label):
                    payload = message.get('payload') if isinstance(message, dict) else None
                    if isinstance(payload, dict):
                        rec = dict(payload)
                        rec['label'] = label
                    else:
                        rec = {'label': label, 'raw': message}
                    self.log(rec)

                script.on('message', on_message)
                script.load()
                self.sessions.append((session, script))
                self.log({'kind': 'injected', 'pid': pid, 'script': label})
            except Exception as exc:  # noqa: BLE001
                self.log({'kind': 'inject_error', 'pid': pid,
                          'script': label, 'error': repr(exc)})

    def wait_and_inject(self, wait, after_ts):
        deadline = time.time() + wait
        injected = set()
        while time.time() < deadline:
            for pid in list_pids(PROCESS_NAME):
                if pid in injected:
                    continue
                st = start_time(pid)
                if after_ts and st and st < after_ts:
                    continue
                self.log({'kind': 'found', 'pid': pid, 'started': st})
                self.inject(pid)
                injected.add(pid)
                return pid, injected
            time.sleep(0.05)
        return None, injected

    def hold(self, duration):
        end = time.time() + duration
        while time.time() < end:
            time.sleep(0.5)

    def close(self):
        for session, script in self.sessions:
            try:
                script.unload()
            except Exception:  # noqa: BLE001
                pass
            try:
                session.detach()
            except Exception:  # noqa: BLE001
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wait', type=float, default=120.0)
    ap.add_argument('--duration', type=float, default=180.0)
    ap.add_argument('--trace', action='store_true')
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'orchestrate.jsonl'))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    started = time.time() - 2.0  # small slack for clock skew
    runner = Runner(args.log, args.trace)
    runner.log({'kind': 'orchestrator_ready', 'since': started})

    try:
        pid, injected = runner.wait_and_inject(args.wait, started)
        if pid is None:
            runner.log({'kind': 'not_found'})
            return 2
        runner.log({'kind': 'holding', 'pid': pid, 'duration': args.duration})
        runner.hold(args.duration)
    except KeyboardInterrupt:
        runner.log({'kind': 'interrupted'})
    finally:
        runner.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())


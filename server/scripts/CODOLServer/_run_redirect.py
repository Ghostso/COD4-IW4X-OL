"""Non-elevated end-to-end runner for the TCLS directory redirect.

What it does
------------
1. Waits for a freshly started tcls_core.exe (started after this script began).
2. Attaches with Frida and installs CODOLServer/frida_tcls_dir_redirect.js.
3. Streams Frida messages to stdout and to a log file for --duration seconds.
4. Optionally also installs CODOLServer/_trace_real_path.js first, to record the
   real socket lifecycle that tcls_core uses for the directory query.

This replaces the elevated PowerShell wrapper for day-to-day iteration: killing
the stale chain is done through Frida (TerminateProcess) rather than taskkill,
which needs no administrator rights on this machine.
"""
import argparse
import json
import os
import sys
import threading
import time

import frida

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


def log_line(path, rec):
    line = json.dumps(rec, ensure_ascii=False, default=str)
    print(line, flush=True)
    if path:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')


def find_new_process(name, since, timeout):
    """Poll for a process named `name` whose start time is after `since`."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for proc in frida.get_local_device().enumerate_processes():
            if proc.name.lower() != name.lower():
                continue
            started = getattr(proc, 'started', None)
            if started is None:
                continue
            started_ts = started.timestamp() if hasattr(started, 'timestamp') else None
            if started_ts is None or started_ts >= since:
                return proc.pid
        time.sleep(0.25)
    return None


def attach(pid, script_path, log_path, label, duration):
    session = frida.attach(pid)
    with open(script_path, 'r', encoding='utf-8') as fh:
        source = fh.read()
    script = session.create_script(source)

    def on_message(message, data):
        rec = {'label': label, 'raw': message}
        payload = message.get('payload') if isinstance(message, dict) else None
        if isinstance(payload, dict):
            rec = dict(payload)
            rec['label'] = label
        log_line(log_path, rec)

    script.on('message', on_message)
    script.load()
    return session, script


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--duration', type=float, default=120.0)
    ap.add_argument('--pid', type=int, default=0,
                    help='attach to this PID instead of waiting for a new one')
    ap.add_argument('--process', default='tcls_core.exe')
    ap.add_argument('--wait', type=float, default=60.0,
                    help='how long to wait for the process to appear')
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'redirect_run.jsonl'))
    ap.add_argument('--trace', action='store_true',
                    help='also install the socket-lifecycle tracer')
    args = ap.parse_args()

    started_at = time.time()
    pid = args.pid
    if not pid:
        print('waiting for %s ...' % args.process, flush=True)
        pid = find_new_process(args.process, started_at, args.wait)
    if not pid:
        print('process not found: %s' % args.process, file=sys.stderr)
        return 2
    print('attaching pid=%d' % pid, flush=True)

    sessions = []
    try:
        if args.trace:
            sessions.append(attach(pid, os.path.join(HERE, '_trace_real_path.js'),
                                   args.log, 'trace', args.duration))
        sessions.append(attach(pid, os.path.join(HERE, 'frida_tcls_dir_redirect.js'),
                               args.log, 'redirect', args.duration))
        deadline = time.time() + args.duration
        while time.time() < deadline:
            if not any(True for _ in ()):
                pass
            time.sleep(0.5)
            try:
                if not any(s[0] for s in sessions):
                    break
            except Exception:  # noqa: BLE001
                break
    except KeyboardInterrupt:
        print('interrupted', flush=True)
    finally:
        for session, _script in sessions:
            try:
                session.detach()
            except Exception:  # noqa: BLE001
                pass
    print('done', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

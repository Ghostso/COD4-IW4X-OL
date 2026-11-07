"""Spawn-gating injector for tcls_core.exe.

Problem
-------
tcls_core only queries the TCLS directory server in the first seconds after
launch (observed: process start 23:41:15, directory query 23:41:31, attach at
23:41:54 -> too late). Attaching after the fact misses every connect().

Solution
--------
Enable Frida spawn gating. Any child process is suspended before its first
instruction, so we can attach while it is still frozen, install the connect
redirect hook, and only then resume it. The redirect is therefore armed before
tcls_core can issue its very first directory connect().

Usage
-----
    python _gate_inject.py --gate-for 120 --inject-duration 180

It prints the gated PIDs as they appear. Launch TGP in another shell while this
is running.
"""
import argparse
import json
import os
import sys
import threading
import time

import frida

HERE = os.path.dirname(os.path.abspath(__file__))

TARGETS = ('tcls_core.exe',)


class Injector:
    def __init__(self, log_path, duration):
        self.log_path = log_path
        self.duration = duration
        self.lock = threading.Lock()
        self.sessions = []
        self.threads = []

    def log(self, rec):
        line = json.dumps(rec, ensure_ascii=False, default=str)
        print(line, flush=True)
        if self.log_path:
            with open(self.log_path, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')

    def on_spawn(self, spawn):
        name = (spawn.name or '').lower()
        if name not in TARGETS:
            # Not our target: resume immediately so nothing is delayed.
            try:
                spawn.resume()
            except Exception:  # noqa: BLE001
                pass
            return
        self.log({'kind': 'spawn_gated', 'pid': spawn.pid, 'name': spawn.name})

        def worker():
            try:
                # Child gating keeps the process suspended; attach first.
                session = frida.attach(spawn.pid)
                session.enable_child_gating()
                with open(os.path.join(HERE, 'frida_tcls_dir_redirect.js'),
                          'r', encoding='utf-8') as fh:
                    source = fh.read()
                script = session.create_script(source)
                script.on('message', lambda m, d: self.log(
                    dict(m.get('payload'), label='redirect')
                    if isinstance(m.get('payload'), dict)
                    else {'raw': m, 'label': 'redirect'}))
                script.load()
                with self.lock:
                    self.sessions.append((session, script))
                self.log({'kind': 'injected_before_resume', 'pid': spawn.pid})
            except Exception as exc:  # noqa: BLE001
                self.log({'kind': 'inject_error', 'pid': spawn.pid, 'error': repr(exc)})
            finally:
                try:
                    spawn.resume()
                    self.log({'kind': 'resumed', 'pid': spawn.pid})
                except Exception as exc:  # noqa: BLE001
                    self.log({'kind': 'resume_error', 'pid': spawn.pid, 'error': repr(exc)})

        try:
            spawn.resume()
        except Exception:  # noqa: BLE001
            pass

    def run(self, gate_for, device):
        device.on('spawn-added', self.on_spawn)
        device.on('child-added', self.on_spawn)
        device.enable_spawn_gating()
        self.log({'kind': 'gating_enabled'})

        deadline = time.time() + gate_for
        while time.time() < deadline:
            time.sleep(0.5)
            pending = device.enumerate_pending_spawn()
            for spawn in pending:
                if (spawn.name or '').lower() in TARGETS:
                    self.on_spawn(spawn)

        self.log({'kind': 'gating_window_closed', 'sessions': len(self.sessions)})
        # Keep the injected sessions alive so the hooks stay armed.
        end = time.time() + self.duration
        while time.time() < end:
            time.sleep(0.5)
        self.close()

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
    ap.add_argument('--gate-for', type=float, default=120.0)
    ap.add_argument('--inject-duration', type=float, default=180.0)
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'gate_inject.jsonl'))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    device = frida.get_local_device()
    inj = Injector(args.log, args.inject_duration)
    try:
        inj.run(args.gate_for, device)
    except KeyboardInterrupt:
        inj.log({'kind': 'interrupted'})
    finally:
        try:
            device.disable_spawn_gating()
        except Exception:  # noqa: BLE001
            pass
        inj.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())

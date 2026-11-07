"""Terminate stale CODOL/TGP test processes via Frida (no admin needed).

Only targets PIDs we identify as our own previous capture runs. Uses
kernel32!ExitProcess through the Frida API with an explicit timeout so it
never hangs the caller.
"""
import sys
import time

import frida

SCRIPT = """
'use strict';
try {
    const ExitProcess = new NativeFunction(
        Module.getExportByName('kernel32.dll', 'ExitProcess'), 'void', ['uint']);
    send({ kind: 'killing', pid: Process.id });
    ExitProcess(0);
} catch (e) {
    send({ kind: 'kill_error', pid: Process.id, error: String(e) });
}
"""


def kill(pid, timeout=6.0):
    try:
        session = frida.attach(pid)
    except Exception as exc:  # noqa: BLE001
        print('attach_failed pid=%d err=%s' % (pid, exc))
        return False
    try:
        script = session.create_script(SCRIPT)
        script.on('message', lambda m, d: print('  msg pid=%d %s' % (pid, m)))
        script.load()
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                session.enumerate_scripts()
            except Exception:  # noqa: BLE001
                break
            time.sleep(0.3)
        return True
    except Exception as exc:  # noqa: BLE001
        print('script_failed pid=%d err=%s' % (pid, exc))
        return False
    finally:
        try:
            session.detach()
        except Exception:  # noqa: BLE001
            pass


def main():
    pids = [int(x) for x in sys.argv[1:]]
    if not pids:
        print('usage: _frida_kill.py <pid> [pid...]')
        return 2
    for pid in pids:
        print('kill pid=%d' % pid)
        kill(pid)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Test whether Frida child-gating works on this Windows host.

Spawns cmd.exe (suspended), attaches, enables child gating, resumes, and waits
for a child process. Prints CHILD_ADDED if a gated child is observed.
"""
import sys
import time

import frida


def main():
    device = frida.get_local_device()
    pid = device.spawn(['cmd.exe', '/c', 'timeout 1 >nul & cmd.exe /c exit'])
    print('spawned parent pid=%d' % pid, flush=True)
    session = device.attach(pid)
    try:
        session.enable_child_gating()
        print('child_gating enabled', flush=True)
    except Exception as exc:  # noqa: BLE001
        print('child_gating failed: %s' % exc, flush=True)
        device.kill(pid)
        return 2

    seen = []

    def on_child(child):
        seen.append(child)
        print('CHILD_ADDED pid=%s name=%s' % (child.pid, child.name), flush=True)
        try:
            device.resume(child.pid)
        except Exception as exc:  # noqa: BLE001
            print('resume child failed: %s' % exc, flush=True)

    device.on('child-added', on_child)
    device.resume(pid)

    deadline = time.time() + 8
    while time.time() < deadline:
        time.sleep(0.2)
        pending = device.enumerate_pending_children()
        for child in pending:
            if child not in seen:
                on_child(child)

    try:
        device.kill(pid)
    except Exception:  # noqa: BLE001
        pass
    print('done children=%d' % len(seen), flush=True)
    return 0 if seen else 1


if __name__ == '__main__':
    sys.exit(main())

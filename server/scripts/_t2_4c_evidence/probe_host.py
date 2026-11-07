"""T-2.4-C harmless probe host.

Deliberately inert: imports only json/os/sys/time, opens no socket, sends no
traffic, loads no CODOL module or plugin, and has no launch/inject/terminate
logic. It exits when the driver creates the stop file, or at its bounded
lifetime, whichever comes first. It writes a handshake document so the driver
can confirm the PID/image it is about to attach to is the process it started.
"""
from __future__ import annotations

import json
import os
import sys
import time


def main() -> int:
    nonce = sys.argv[1]
    handshake_path = sys.argv[2]
    stop_path = sys.argv[3]
    max_seconds = float(sys.argv[4])

    record = {
        "pid": os.getpid(),
        "nonce": nonce,
        "executable": sys.executable,
        "script": os.path.abspath(__file__),
        "argv": list(sys.argv),
        "started_at": time.time(),
    }
    with open(handshake_path, "w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)

    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        if os.path.exists(stop_path):
            return 0
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

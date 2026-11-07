"""Run one clean round while sampling the client's pump for the whole
post-0x83 idle window (default 70 s), to see whether any inbound frame is
ever decoded before the ~52 s lobby watchdog fires.

Read-only: the observer only reads process memory; the probe only serves the
handshake.  No writes to [req+0x644] and no extra opcodes are injected.

Usage:
  python -X utf8 CODOLServer/_mainline/_post83_long_observe.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
LS = os.path.join(ROOT, "CODOLServer", "lobby_server")
MAINLINE = os.path.join(ROOT, "CODOLServer", "_mainline")
PY = sys.executable


def main() -> int:
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(ROOT, "CODOLServer", "logs",
                           "POST83_LONG_%s" % ts)
    os.makedirs(log_dir, exist_ok=True)
    plain_log = os.path.join(log_dir, "plain.jsonl")
    ready = os.path.join(log_dir, "ready.flag")
    echo = os.path.join(log_dir, "echo.txt")

    probe = os.path.join(LS, "lobby_plain_probe.py")
    pout = open(os.path.join(log_dir, "plain.stdout.log"), "ab")
    perr = open(os.path.join(log_dir, "plain.stderr.log"), "ab")
    p = subprocess.Popen(
        [PY, "-X", "utf8", "-u", probe,
         "--bind", "127.0.0.1", "--port", "8446",
         "--log", plain_log, "--lobby-handshake",
         "--magic", "0xDC", "--token", "0x1122334455667788",
         "--ready-file", ready, "--ready-timeout", "90",
         "--echo-file", echo, "--hold-after-83", "70"],
        stdout=pout, stderr=perr)
    print("plain probe pid", p.pid, "log", log_dir, flush=True)
    time.sleep(2.0)

    loop = os.path.join(MAINLINE, "auto_lobby_loop.py")
    argv = [PY, "-X", "utf8", "-u", loop,
            "--rounds", "1", "--seconds", "110",
            "--poke-lobby-host", "127.0.0.1",
            "--poke-lobby-port", "8443", "--poke-lobby-globals",
            "--lobby-ready-only",
            "--handshake-ready-file", ready,
            "--handshake-echo-file", echo,
            "--post83-trace", "--post83-seconds", "70",
            "--abort-on-cfg0"]
    r = subprocess.run(argv, cwd=MAINLINE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")

    try:
        p.terminate()
    except Exception:
        pass
    time.sleep(1.0)
    if p.poll() is None:
        p.kill()
    pout.close()
    perr.close()
    print("driver done; log dir:", log_dir, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Minimal UDP listener used to capture the client's STUN probe bytes.

Binds 0.0.0.0:<port> and appends every datagram (with peer and hex payload)
to a JSONL log so we can learn what the client actually sends before writing
a responder.  Read-only w.r.t. the game; it only listens.

Usage:
  python -X utf8 CODOLServer/_mainline/_stun_capture.py --port 3074 \
      --log <abs.jsonl> [--reply-hex <hex>] [--seconds 200]
"""
from __future__ import annotations

import argparse
import json
import socket
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3074)
    ap.add_argument("--log", required=True)
    ap.add_argument("--reply-hex", default="",
                    help="if set, send these bytes back to each sender")
    ap.add_argument("--reply-echo", action="store_true",
                    help="if set, echo each datagram back to its sender")
    ap.add_argument("--seconds", type=float, default=200.0)
    a = ap.parse_args()
    reply = bytes.fromhex(a.reply_hex.replace(" ", "")) if a.reply_hex else b""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((a.bind, a.port))
    s.settimeout(1.0)
    log(a.log, {"event": "listen", "bind": a.bind, "port": a.port,
                "reply_hex": reply.hex(), "reply_echo": a.reply_echo})
    end = time.time() + a.seconds
    n = 0
    while time.time() < end:
        try:
            data, peer = s.recvfrom(2048)
        except socket.timeout:
            continue
        except OSError as exc:
            log(a.log, {"event": "error", "error": str(exc)})
            break
        n += 1
        log(a.log, {"event": "recv", "peer": list(peer), "len": len(data),
                    "hex": data.hex()})
        if reply or a.reply_echo:
            out = data if a.reply_echo else reply
            try:
                s.sendto(out, peer)
                log(a.log, {"event": "sent_reply", "peer": list(peer),
                            "len": len(out), "hex": out.hex()})
            except OSError as exc:
                log(a.log, {"event": "send_error", "error": str(exc)})
    log(a.log, {"event": "done", "count": n})
    return 0


def log(path: str, obj: dict) -> None:
    obj = dict(obj)
    obj["ts"] = time.time()
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

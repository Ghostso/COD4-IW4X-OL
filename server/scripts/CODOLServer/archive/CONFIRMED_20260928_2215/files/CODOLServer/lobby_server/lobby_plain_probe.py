#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plain-TCP lobby channel probe.

The client's lobby channel (built by 0x007F3800, connected by 0x00C73900 via
the Tenio connector) is NOT TLS: when it landed on the HTTPS probe server the
server logged "WRONG_VERSION_NUMBER".  This listener accepts the raw socket,
hex-dumps everything the client sends, and can send canned replies so the
0x00BA41D0 state machine can be observed.

Usage:
  python -X utf8 lobby_plain_probe.py --bind 127.0.0.1 --port 8445 \
      --log logs/lobby_plain.jsonl
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time


def log(path: str, obj: dict) -> None:
    obj["ts"] = time.time()
    line = json.dumps(obj, ensure_ascii=False)
    print(line, flush=True)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def hexdump(b: bytes) -> str:
    return " ".join("%02x" % x for x in b)


def serve_conn(conn: socket.socket, peer, path: str, reply: bytes,
               hold: bool = True, repeat_every: float = 0.0) -> None:
    conn.settimeout(20.0)
    log(path, {"event": "accept", "peer": list(peer)})
    total = bytearray()
    next_repeat = time.time() + repeat_every if repeat_every > 0 else 0.0
    try:
        while True:
            if repeat_every > 0 and reply and time.time() >= next_repeat:
                # 0xBA20A0 keeps the session alive only while server frames keep
                # arriving; with a single reply the client drops the lobby ~50 s
                # later with "与大厅服务失去连接".
                try:
                    conn.sendall(reply)
                    log(path, {"event": "repeat_sent", "peer": list(peer),
                               "len": len(reply), "hex": hexdump(reply[:64])})
                except OSError as exc:
                    log(path, {"event": "repeat_error", "peer": list(peer),
                               "error": str(exc)})
                    break
                next_repeat = time.time() + repeat_every
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                # The client treats a dead lobby channel as fatal a short while
                # later, so keep the socket open across idle periods and just
                # note them.  Closing here produced the "致命错误" dialog.
                log(path, {"event": "recv_timeout", "peer": list(peer),
                           "total": len(total), "holding": hold})
                if not hold:
                    break
                continue
            if not chunk:
                break
            total += chunk
            log(path, {"event": "recv", "peer": list(peer),
                       "len": len(chunk), "hex": hexdump(chunk[:2048]),
                       "total": len(total)})
            if reply:
                try:
                    conn.sendall(reply)
                    log(path, {"event": "sent", "peer": list(peer),
                               "len": len(reply), "hex": hexdump(reply[:512])})
                except OSError as exc:
                    log(path, {"event": "send_error", "peer": list(peer),
                               "error": str(exc)})
    except OSError as exc:
        log(path, {"event": "conn_error", "peer": list(peer),
                   "error": str(exc)})
    finally:
        log(path, {"event": "close", "peer": list(peer), "total": len(total),
                   "full_hex": hexdump(total[:8192])})
        try:
            conn.close()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8445)
    ap.add_argument("--log", default="")
    ap.add_argument("--reply-hex", default="",
                    help="hex bytes to send back after each received chunk")
    ap.add_argument("--repeat-every", type=float, default=0.0,
                    help="also re-send the reply every N seconds")
    a = ap.parse_args()
    reply = bytes.fromhex(a.reply_hex) if a.reply_hex else b""

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.bind, a.port))
    srv.listen(16)
    log(a.log, {"event": "listen", "bind": a.bind, "port": a.port,
                "pid": __import__("os").getpid()})
    try:
        while True:
            conn, peer = srv.accept()
            threading.Thread(target=serve_conn,
                             args=(conn, peer, a.log, reply, True,
                                   a.repeat_every),
                             daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

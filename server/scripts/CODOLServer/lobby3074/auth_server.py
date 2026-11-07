# -*- coding: utf-8 -*-
"""CODOL /auth/ TLS server on 127.0.0.1:3074.

Serves POST /auth/ over TLS. Per CODOL_LOBBY_WORKING_20261002.md section 9,
the reply must report task=10->11; auth_task=32 means the client went down the
TAS (signed) path and will never reach the lobby.

The response body format is not specified in the doc beyond that, so the
default here is the same shape our existing lobby_probe_server used; it is
overridable with --response-file.
"""
import argparse
import json
import os
import socket
import ssl
import sys
import threading
import time


class Log(object):
    def __init__(self, path):
        self.lock = threading.Lock()
        self.fh = open(path, "a", encoding="utf-8") if path else None

    def __call__(self, msg):
        line = "%.3f %s" % (time.time(), msg)
        with self.lock:
            print(line, flush=True)
            if self.fh:
                self.fh.write(line + "\n")
                self.fh.flush()


def build_body(reply_id=1, task_in=10, task_out=11, extra=None):
    """Minimal JSON auth reply. task_out=11 is the documented success marker."""
    d = {
        "ret": 0,
        "task": task_out,
        "auth_task": task_out,
        "replyId": reply_id,
    }
    if extra:
        d.update(extra)
    return json.dumps(d).encode("utf-8")


def http_response(body, ctype="application/json"):
    hdr = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n"
    ) % (ctype, len(body))
    return hdr.encode("ascii") + body


def serve(bind, port, cert, key, log, body_fn):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    try:
        ctx.set_ciphers("ALL:@SECLEVEL=0")
    except ssl.SSLError:
        pass

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((bind, port))
    srv.listen(8)
    log("=== auth TLS listening on %s:%d ===" % (bind, port))
    log("    cert=%s key=%s" % (cert, key))

    while True:
        c, a = srv.accept()
        t = threading.Thread(target=session, args=(c, a, ctx, log, body_fn),
                             daemon=True)
        t.start()


def session(c, a, ctx, log, body_fn):
    log("=== auth connection from %s:%d ===" % a)
    try:
        s = ctx.wrap_socket(c, server_side=True)
    except Exception as e:
        log("!! TLS handshake failed: %s" % e)
        c.close()
        return
    try:
        s.settimeout(5.0)
        req = b""
        while b"\r\n\r\n" not in req and len(req) < 65536:
            d = s.recv(4096)
            if not d:
                break
            req += d
        head = req.split(b"\r\n\r\n", 1)[0].decode("latin1", "replace")
        first = head.splitlines()[0] if head else ""
        log("<-- %s" % first)
        body = body_fn(req)
        s.sendall(http_response(body))
        log("--> 200 (%d bytes)" % len(body))
        try:
            s.unwrap()
        except Exception:
            pass
    except Exception as e:
        log("!! session error: %s" % e)
    finally:
        try:
            s.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3074)
    ap.add_argument("--cert", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--response-file", default="")
    ap.add_argument("--task-out", type=int, default=11)
    a = ap.parse_args()
    log = Log(a.log)

    if a.response_file and os.path.isfile(a.response_file):
        raw = open(a.response_file, "rb").read()

        def body_fn(_req, raw=raw):
            return raw

        log("using fixed response from %s" % a.response_file)
    else:
        counter = {"n": 0}
        lock = threading.Lock()

        def body_fn(req):
            with lock:
                counter["n"] += 1
                n = counter["n"]
            return build_body(reply_id=n, task_out=a.task_out)

    serve(a.bind, a.port, a.cert, a.key, log, body_fn)


if __name__ == "__main__":
    main()

"""Minimal CODOL lobby socket server.

Listens on 127.0.0.2:8444 (via portproxy 127.0.0.2:443 -> 8444).
Accepts TLS connections from the game client after successful /auth/.
Validates the client_ticket (must start with NULL_REF tag DE AD BD EF).
ASCII only.
"""
import argparse
import json
import os
import socket
import ssl
import sys
import threading
import time

NULL_REF = b"\xDE\xAD\xBD\xEF"  # 0xEFBDADDE little-endian
TICKET_LEN = 128

try:
    from mklobby_response import TASK_ANSWER
except Exception:                                    # pragma: no cover
    TASK_ANSWER = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 33}


class Logger:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        try:
            self.echo = bool(getattr(sys.stdout, "isatty", lambda: False)())
        except Exception:
            self.echo = False
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def __call__(self, obj):
        obj["ts"] = time.time()
        line = json.dumps(obj, ensure_ascii=False)
        with self.lock:
            if self.echo:
                try:
                    print(line, flush=True)
                except Exception:
                    pass
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")


def handle(conn, addr, log):
    peer = list(addr)
    log({"event": "connect", "peer": peer})
    try:
        # Read HTTP request first
        request = b""
        while b"\r\n\r\n" not in request and len(request) < 8192:
            chunk = conn.recv(1024)
            if not chunk:
                break
            request += chunk
        
        if not request:
            # The first TLS connection the client makes sends nothing at all.
            # Closing it immediately is what produced "empty_request" and
            # forced the client to retry.  Hold it open and log whatever
            # arrives instead of rejecting.
            log({"event": "empty_hold", "peer": peer,
                 "note": "client sent nothing; holding socket open"})
            conn.settimeout(20.0)
            while True:
                try:
                    more = conn.recv(4096)
                except socket.timeout:
                    log({"event": "empty_timeout", "peer": peer})
                    break
                except Exception as e:
                    log({"event": "empty_error", "peer": peer,
                         "error": repr(e)})
                    break
                if not more:
                    log({"event": "empty_closed", "peer": peer})
                    break
                log({"event": "empty_data", "peer": peer,
                     "len": len(more), "hex": more[:512].hex()})
                request = more
                break
        if not request:
            return
        
        # Parse request line
        lines = request.split(b"\r\n")
        request_line = lines[0].decode("latin1", "replace") if lines else ""
        log({"event": "http_request", "peer": peer, "request_line": request_line})
        
        # Parse method and path
        parts = request_line.split()
        method = parts[0] if len(parts) > 0 else ""
        path = parts[1] if len(parts) > 1 else ""
        
        # Health check: GET / or GET /health
        if method == "GET" and path in ("/", "/health", ""):
            log({"event": "health_check", "peer": peer})
            # EXPERIMENT: do NOT close after the probe reply.  The client
            # opened a first TLS connection that sent nothing, then a second
            # one with "GET /", and then gave up right after our empty 200 +
            # Connection: close.  Hold the connection open and log whatever
            # it sends next, so we can see whether the real lobby handshake
            # follows on this socket.
            resp = (b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n"
                    b"Connection: keep-alive\r\n\r\n")
            conn.sendall(resp)
            log({"event": "health_check_ok", "peer": peer,
                 "note": "holding connection open"})
            conn.settimeout(20.0)
            while True:
                try:
                    more = conn.recv(4096)
                except socket.timeout:
                    log({"event": "hold_timeout", "peer": peer})
                    break
                except Exception as e:
                    log({"event": "hold_error", "peer": peer,
                         "error": repr(e)})
                    break
                if not more:
                    log({"event": "hold_closed", "peer": peer})
                    break
                log({"event": "hold_data", "peer": peer,
                     "len": len(more), "hex": more[:512].hex()})
                # Late request on the same socket: answer it too.
                if b"\r\n" in more:
                    try:
                        conn.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n"
                            b"Connection: keep-alive\r\n\r\n")
                    except Exception:
                        break
            return
        
        # Parse headers
        headers = {}
        body_start = 0
        for i, ln in enumerate(lines[1:], 1):
            if not ln:
                body_start = i + 1
                break
            k, _, v = ln.partition(b":")
            headers[k.strip().lower()] = v.strip()

        # The client sends "Expect: 100-continue" on POST /auth/.  If we do
        # not answer it the client waits out its own timer (~14s, seen in the
        # san1 log) before sending the body, and we read 0 bytes and report
        # incomplete_ticket.  RFC 7231: reply 100 Continue as soon as the
        # headers are accepted.
        if b"100-continue" in headers.get(b"expect", b"").lower():
            try:
                conn.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
                log({"event": "sent_100_continue", "peer": peer})
            except Exception as e:
                log({"event": "100_continue_failed", "peer": peer,
                     "error": repr(e)})
        
        # Find body
        body = b""
        if body_start < len(lines):
            body = b"\r\n".join(lines[body_start:])
        else:
            # Body might be after the headers in the request buffer
            header_end = request.find(b"\r\n\r\n")
            if header_end >= 0:
                body = request[header_end + 4:]
        
        # Parse Content-Length
        content_length = 0
        cl_header = headers.get(b"content-length")
        if cl_header:
            try:
                content_length = int(cl_header.strip())
            except ValueError:
                pass
        
        # Read remaining body if needed
        while len(body) < content_length:
            chunk = conn.recv(content_length - len(body))
            if not chunk:
                break
            body += chunk
        
        # Health check: GET / or GET /health
        if method == "GET" and path in ("/", "/health", ""):
            log({"event": "health_check", "peer": peer})
            resp = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            conn.sendall(resp)
            log({"event": "health_check_ok", "peer": peer})
            return
        
        # Ticket exchange: accept JSON ticket in HTTP POST body
        ticket_data = None
        # The client sends the SAME POST /auth/ JSON to the lobby host that it
        # sends to the /auth/ probe (dwauth.ini field 3 is the lobby host).
        # Treating that body as a raw 128-byte ticket is what produced
        # "incomplete_ticket" after a 14 s stall.  Answer it with the auth
        # contract instead.
        if method == "POST" and path.startswith("/auth"):
            try:
                req = json.loads(body.decode("utf-8"))
            except Exception:
                req = {}
            raw_task = req.get("auth_task")
            try:
                stage = int(str(raw_task).strip())
            except (TypeError, ValueError):
                stage = None
            ans = TASK_ANSWER.get(stage, stage if stage is not None else 1)
            # Reuse the exact same template the /auth/ probe serves; a minimal
            # {auth_task,code,iv_seed} body is NOT enough - the client then
            # reports 735 (0x2DF) because the ticket fields are missing.
            tmpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "lobby_response.json")
            payload = None
            try:
                with open(tmpl_path, "rb") as fh:
                    payload = fh.read()
                payload = payload.replace(b"$AUTH_TASK", str(ans).encode())
                seed = req.get("iv_seed", 0)
                try:
                    seed = str(int(str(seed).strip())).encode()
                except (TypeError, ValueError):
                    seed = b"0"
                payload = payload.replace(b"$IV_SEED", seed)
                json.loads(payload.decode("utf-8"))
            except Exception as e:
                log({"event": "auth_template_failed", "peer": peer,
                     "error": repr(e)})
                payload = None
            if payload is None:
                payload = ('{"auth_task":%d,"code":700,"iv_seed":%s}'
                           % (ans, json.dumps(req.get("iv_seed", 0)))).encode()
            resp = (b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(payload)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n" + payload)
            log({"event": "auth_on_lobby_port", "peer": peer,
                 "req_auth_task": raw_task, "resp_auth_task": ans})
            conn.sendall(resp)
            while True:
                try:
                    more = conn.recv(4096)
                except Exception:
                    break
                if not more:
                    break
                log({"event": "after_auth_data", "peer": peer,
                     "len": len(more), "hex": more[:512].hex()})
            return

        if method == "POST" and body:
            try:
                ticket_json = json.loads(body.decode("utf-8"))
                # Expect {"ticket": "<base64_encoded_128_bytes>"} or {"ticket": "<base64>"}
                # Or raw base64 string
                ticket_b64 = ticket_json.get("ticket")
                if ticket_b64:
                    import base64
                    try:
                        data = base64.b64decode(ticket_b64)
                    except Exception:
                        data = None
                else:
                    # Try raw body as base64
                    try:
                        data = base64.b64decode(body)
                    except Exception:
                        data = None
            except Exception as e:
                log({"event": "error", "peer": peer, "reason": "json_parse_error", "error": str(e)})
                data = None
        
        # Fallback: raw 128-byte ticket (no HTTP)
        if data is None:
            # Read raw ticket data
            data = b""
            while len(data) < TICKET_LEN:
                chunk = conn.recv(TICKET_LEN - len(data))
                if not chunk:
                    break
                data += chunk
                log({"event": "ticket_chunk", "peer": peer, "chunk_len": len(chunk), "total_len": len(data)})
        
        log({"event": "ticket_recv", "peer": peer, "len": len(data), "data_hex": data.hex()[:120]})

        if len(data) != TICKET_LEN:
            log({"event": "error", "peer": peer, "reason": "incomplete_ticket", "got": len(data)})
            conn.sendall(b"\x00")  # failure
            return

        # Validate NULL_REF tag
        if data[:4] != NULL_REF:
            log({"event": "error", "peer": peer, "reason": "bad_null_ref", "got": data[:4].hex()})
            conn.sendall(b"\x00")  # failure
            return

        log({"event": "ticket_valid", "peer": peer})
        conn.sendall(b"\x01")  # success

    except Exception as e:
        log({"event": "error", "peer": peer, "error": repr(e)})
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cert-dir", default=".")
    ap.add_argument("--bind", default="127.0.0.2")
    ap.add_argument("--port", type=int, default=8444)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    cert = os.path.join(a.cert_dir, "lobby_server.pem")
    key = os.path.join(a.cert_dir, "lobby_server.key")
    if not (os.path.exists(cert) and os.path.exists(key)):
        print("missing cert/key; run mklobby_cert.py first", file=sys.stderr)
        return 2

    log = Logger(a.log)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    # Allow legacy TLS 1.0 for the game client
    try:
        ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
    except Exception:
        pass
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except Exception:
        pass
    try:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    except Exception:
        pass
    try:
        ctx.options |= ssl.OP_NO_TLSv1_3
    except Exception:
        pass

    log({"event": "tls_config", "bind": a.bind, "port": a.port})

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Windows: SO_REUSEADDR would let a stale instance share this port, and
    # the OS then hands each new connection to an arbitrary one of the two
    # listeners.  That is exactly what made the lobby reach
    # "connecting to server" on one run and fall back to
    # "cannot connect to lobby" on the next.  Bind exclusively instead.
    try:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    except (AttributeError, OSError):
        pass
    try:
        srv.bind((a.bind, a.port))
    except OSError as e:
        log({"event": "fatal", "stage": "bind", "bind": a.bind,
             "port": a.port, "error": repr(e),
             "hint": "another instance is already listening; kill it first"})
        print("bind failed: %r (is another instance running?)" % e,
              file=sys.stderr)
        return 3
    srv.listen(32)
    log({"event": "listen", "bind": a.bind, "port": a.port, "pid": os.getpid()})

    while True:
        try:
            s, addr = srv.accept()
        except KeyboardInterrupt:
            break
        # Perform the TLS handshake explicitly.  The lobby client expects a
        # completed handshake before it sends anything, so the lazy wrapper is
        # not enough (SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md: "the key fix
        # is conn.do_handshake()").
        #
        # The earlier attempt at this "broke" the lobby only because the log()
        # line inside the try block referenced an undefined name, so the except
        # branch tore down a perfectly good connection.  Log with the real peer
        # and keep the two concerns separate.
        peer = list(addr)
        try:
            conn = ctx.wrap_socket(s, server_side=True)
            conn.settimeout(15.0)
            conn.do_handshake()
            log({"event": "tls_wrapped", "peer": peer,
                 "version": conn.version(),
                 "cipher": (conn.cipher() or (None,))[0]})
        except Exception as e:
            log({"event": "tls_fail", "peer": peer, "error": repr(e)})
            try:
                s.close()
            except Exception:
                pass
            continue
        threading.Thread(target=handle, args=(conn, addr, log), daemon=True).start()


if __name__ == "__main__":
    sys.exit(main())

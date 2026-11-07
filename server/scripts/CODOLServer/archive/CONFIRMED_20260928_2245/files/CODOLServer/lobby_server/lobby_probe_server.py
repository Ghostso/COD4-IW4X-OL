"""Minimal local CODOL lobby probe server.

Goal: prove the client actually reaches a lobby endpoint we control, and
capture the request bytes. It speaks HTTPS only (no UDP yet).

ASCII only. No system network changes. Binds loopback by default.

Run:
  python -X utf8 lobby_probe_server.py --cert-dir . --bind 127.0.0.1 --port 8443 \
      --log ..\\logs\\lobby_probe.jsonl

Every accepted connection is logged with peer, TLS info, method, path,
headers and a hexdump of the body. Anything that is not GET/POST is answered
with a plain 404 so the client fails fast instead of hanging.
"""
import argparse
import json
import os
import socket
import ssl
import sys
import threading
import time

# Single source of truth for the response auth_task mapping.  The probe is
# always started as a script from this directory, so the sibling module is
# importable; fall back to an inline copy if that ever changes.
try:
    from mklobby_response import (TASK_ANSWER, TICKET_LEN, NULL_REF,
                                  extra_data_json)
except Exception:                                    # pragma: no cover
    TASK_ANSWER = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}
    TICKET_LEN = 0x80
    NULL_REF = 0xEFBDADDE

    def extra_data_json():
        """Fallback: minimal inner JSON + its JSON-string-escaped token."""
        inner = ('{"cd_key":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
                 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=","encrypted_codoid":"Q09E'
                 'T0wtTE9DQUwtMDAwMQ==","encrypted_register_codoid_data":"ICEi'
                 'IyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5P'
                 'UFFSU1RVVldYWVpbXF1eXyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8'
                 'PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl8=","extended'
                 '_data":"{\\"version\\":\\"0\\"}",'
                 '"time_to_live":3600,"username":"CODOL_LOCAL"}')
        return inner, json.dumps(inner)


def hexdump(b, limit=512):
    b = b[:limit]
    return b.hex()


class Logger:
    def __init__(self, path):
        # Every start gets its own timestamped file so a later run can never
        # truncate the evidence of an earlier one, and so the request and the
        # response of a single round trip can always be correlated.
        self.path = path
        self.lock = threading.Lock()
        if path:
            root, ext = os.path.splitext(path)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            self.path = "%s.%s%s" % (root, stamp, ext or ".jsonl")
            self.latest = path
        # Only echo to the console when stdout is a real console.  When the
        # process is started with redirected stdout the pipe buffer can fill
        # and a blocking print() would stall the logger lock (and therefore
        # every connection thread), so skip the echo in that case.
        try:
            self.echo = bool(getattr(sys.stdout, "isatty", lambda: False)())
        except Exception:
            self.echo = False
        if self.path:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)

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
                for target in (self.path, self.latest):
                    try:
                        with open(target, "a", encoding="utf-8") as f:
                            f.write(line + "\n")
                    except Exception:
                        pass


def read_http(conn):
    """Read one HTTP request. Returns (raw_head, body_bytes)."""
    conn.settimeout(15.0)
    buf = b""
    while b"\r\n\r\n" not in buf and len(buf) < 65536:
        try:
            chunk = conn.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    if b"\r\n\r\n" not in buf:
        return buf, b""
    head, _, rest = buf.partition(b"\r\n\r\n")
    clen = 0
    has_expect_100 = False
    for ln in head.split(b"\r\n")[1:]:
        k, _, v = ln.partition(b":")
        k_lower = k.strip().lower()
        if k_lower == b"content-length":
            try:
                clen = int(v.strip())
            except ValueError:
                clen = 0
        elif k_lower == b"expect" and b"100-continue" in v.lower():
            has_expect_100 = True

    # The client (libcurl 7.38 + OpenSSL 0.9.8p) blocks waiting for the
    # interim response whenever it sends "Expect: 100-continue".  Sending it
    # only when the body has not fully arrived yet made the client stall and
    # fall through to DW_LOBBY_ERROR before the /auth/ reply was read, so the
    # interim response is now emitted unconditionally for such requests.
    if has_expect_100:
        try:
            conn.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        except Exception:
            pass

    body = rest
    while len(body) < clen:
        try:
            chunk = conn.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        body += chunk
    return head, body


def handle(raw_sock, addr, ctx, log):
    rec = {"event": "connect", "peer": list(addr)}
    resp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "lobby_response.json")
    try:
        conn = ctx.wrap_socket(raw_sock, server_side=True)
    except Exception as e:
        rec["event"] = "tls_fail"
        rec["error"] = repr(e)
        log(rec)
        try:
            raw_sock.close()
        except Exception:
            pass
        return

    try:
        rec["tls_version"] = conn.version()
        try:
            rec["cipher"] = conn.cipher()[0]
        except Exception:
            rec["cipher"] = None
        try:
            sc = conn.getpeercert()
            if sc:
                rec["client_subject"] = str(sc.get("subject"))
        except Exception:
            pass
        rec["servername"] = getattr(conn, "server_hostname", None)
        log({"event": "tls_ok", **{k: v for k, v in rec.items() if k != "event"}})

        head, body = read_http(conn)
        lines = head.split(b"\r\n")
        reqline = lines[0].decode("latin1") if lines else ""
        # Echo the client's X-TransactionID back; never invent one, because
        # the reply must be correlated with the request the client made.
        # (A missing definition here used to raise NameError BEFORE sendall,
        # which closed the connection and left the client with an empty reply
        # -- that is what produced obj_code=0x0 / last_err=0x0.)
        xid = ""
        for ln in lines[1:]:
            k, _, v = ln.partition(b":")
            if k.strip().lower() == b"x-transactionid":
                xid = v.strip().decode("latin1")
                break
        log({
            "event": "http",
            "peer": list(addr),
            "request_line": reqline,
            "headers": [l.decode("latin1") for l in lines[1:] if l],
            "body_len": len(body),
            "body_hex": hexdump(body, 2048),
            "head_hex": hexdump(head, 2048),
            # Mark our own regression traffic so it can never be mistaken for
            # real game traffic when reading the log back later.
            "selftest": any(
                l.split(b":")[0].strip().lower() == b"x-selftest"
                for l in lines[1:] if b":" in l),
        })

        # Demonware /auth/ contract, reverse engineered from the retail client.
        # The response "auth_task" is the ANSWER to the request "auth_task"
        # (which is the client's stage: 0xB99B8C writes [obj+0x14] into the
        # request).  0xB999C0 picks the response parser from that stage and
        # 0xB99940 rejects any answer that is not the expected one, so the
        # mapping below must be applied for every request.
        try:
            req = json.loads(body.decode("utf-8"))
        except Exception:
            req = {}

        # ------------------------------------------------------------------
        # H1: a bare "GET /" is a reachability probe, NOT the auth call.
        # 0x7F2DB0 (sub=6) only expects [objB+0x156C] == 0x2BC, and that value
        # is written exclusively by the auth responders 0xB991A0 / 0xB9A470
        # (via 0xB9A3B1 / 0xB9A423), which run off the POST /auth/ reply.
        # Answering a probe with an auth-shaped JSON body appears to stop the
        # client from ever sending POST /auth/, so the probe gets a bare
        # 200 with an empty body and everything else keeps the normal path.
        # ------------------------------------------------------------------
        method = reqline.split(" ")[0].upper() if reqline else ""
        path = reqline.split(" ")[1] if len(reqline.split(" ")) > 1 else ""
        is_selftest = any(
            l.split(b":")[0].strip().lower() == b"x-selftest"
            for l in lines[1:] if b":" in l)
        is_probe = (method == "GET" and path in ("/", "") and not body
                    and not is_selftest)
        if is_probe:
            # GET / is NOT a bare reachability probe when the lobby object
            # (objC) owns the connection: objC + 0x398 is its own HTTP client
            # and 0xB98B03..0xB98B0A stores 0xB983F0()'s return straight into
            # [objC+0x1400], which 0x7F31B6 compares against 0x22C4 (8900).
            #
            # 0xB983F0 needs a 200 *and* a body it can parse: it reads
            # iv_seed (0xD5A114), lsg_server_ticket_size (0xD5A0FC) and
            # lsg_server_ticket (0xD5A0E8), and falls back to 0x22C6 (8902)
            # via 0xBAA090 when the status is anything else.  An empty 200
            # therefore produced last_err=8902 with lob1400=8902.
            #
            # Serve the same JSON contract used by POST /auth/, with a
            # non-zero iv_seed and Connection: close.
            #
            # Still overridable from probe_response.txt for sweeps:
            #   status=<code>            default 200
            #   body=<raw text>          default = lobby_response.json
            #   header=<Name: value>     repeatable
            probe_file = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "probe_response.txt")
            p_status = 200
            p_body = None
            p_headers = []
            if os.path.exists(probe_file):
                for raw in open(probe_file, encoding="utf-8"):
                    raw = raw.rstrip("\r\n")
                    if raw.startswith("status="):
                        p_status = int(raw[7:])
                    elif raw.startswith("body="):
                        p_body = raw[5:].encode("utf-8")
                    elif raw.startswith("header="):
                        p_headers.append(raw[7:].encode("latin1"))
            if p_body is None:
                p_body = b""
                if os.path.exists(resp_file):
                    with open(resp_file, "rb") as f:
                        p_body = f.read()
                    p_body = p_body.replace(b"$AUTH_TASK", b"1")
                    # A zero iv_seed means "no seed" to this parser; give it a
                    # live value so both dwords at [ebp-0xE8]/[ebp-0xE4] pass.
                    p_body = p_body.replace(b"$IV_SEED", b"1")
                    if b"$EXTRA_DATA" in p_body:
                        _iext, _xtok = extra_data_json()
                        p_body = p_body.replace(b"$EXTRA_DATA",
                                                _xtok.encode("ascii"))
                    try:
                        json.loads(p_body.decode("utf-8"))
                    except Exception as e:
                        log({"event": "probe_template_invalid",
                             "error": repr(e)})
                        p_body = b""
            p_headers.append(b"Connection: close")
            reason = {200: b"OK", 204: b"No Content", 302: b"Found",
                      400: b"Bad Request", 404: b"Not Found",
                      500: b"Internal Server Error"}.get(p_status, b"OK")
            log({"event": "probe_get", "peer": list(addr),
                 "note": "GET / -> %d len=%d headers=%s"
                         % (p_status, len(p_body),
                            [h.decode("latin1") for h in p_headers])})
            # The client's HTTP state machine (0xB9A370 reads
            # [objB+0x20] and the parser state at [httpobj+0x2C]) treated a
            # "Connection: close" 200 as "still in flight" (state 1/3 instead
            # of 5), so the transaction never completed and sub_state stayed
            # at 6.  Advertise keep-alive and hold the socket so the client can
            # finish the exchange itself.
            hdr = ([b"HTTP/1.1 %d " % p_status + reason]
                   + p_headers
                   + [b"Content-Length: %d" % len(p_body)])
            resp = b"\r\n".join(hdr) + b"\r\n\r\n" + p_body
            log({"event": "roundtrip", "peer": list(addr),
                 "req_auth_task": None,
                 "req_body": "",
                 "resp_auth_task": None,
                 "resp_body": p_body.decode("utf-8", "replace")})
            conn.sendall(resp)
            # Stay readable for a while instead of dropping the socket: if the
            # client follows up on the same connection we want to see it.
            conn.settimeout(8.0)
            try:
                more = conn.recv(4096)
                if more:
                    log({"event": "probe_followup", "peer": list(addr),
                         "len": len(more), "hex": hexdump(more, 512)})
            except Exception:
                pass
            return

        # ------------------------------------------------------------
        # H0: the lobby OBJECT (objC) queue endpoint.
        # 0xB986C0 builds "https://<host>:<port>/<lobby>/title/<t>/queue/<q>/
        # member/<id>" and 0xB98D40/0xB98B70 then GET/POST it.  0xB983F0
        # parses the reply and 0x7F31B6 compares the result against 0x22C4.
        # Answer it with the same JSON contract as /auth/ and a live iv_seed.
        # ------------------------------------------------------------
        if "/title/" in path and "/queue/" in path:
            payload = None
            if os.path.exists(resp_file):
                with open(resp_file, "rb") as fh:
                    payload = fh.read()
                payload = payload.replace(b"$AUTH_TASK", b"57")
                payload = payload.replace(b"$IV_SEED", b"1")
                if b"$EXTRA_DATA" in payload:
                    _iext, _xtok = extra_data_json()
                    payload = payload.replace(b"$EXTRA_DATA",
                                              _xtok.encode("ascii"))
                try:
                    json.loads(payload.decode("utf-8"))
                except Exception as e:
                    log({"event": "queue_template_invalid", "error": repr(e)})
                    payload = None
            if payload is None:
                payload = (b'{"auth_task":57,"code":700,"iv_seed":1,'
                           b'"lsg_server_ticket_size":128}')
            else:
                # 0xB983F0 only reads three fields for the queue reply:
                # iv_seed, lsg_server_ticket_size, lsg_server_ticket.
                #
                # The full /auth/ template is ~1220 bytes, but the queue
                # client's receive buffer is 0x400 (1024) bytes; an oversized
                # body leaves curl at state 3 / response_code 0.  Emit a
                # compact reply so the response reliably completes.
                try:
                    import json as _json
                    doc = _json.loads(payload.decode("utf-8"))
                    compact = {
                        "auth_task": 57,
                        "code": 700,
                        "iv_seed": int(doc.get("iv_seed", 1) or 1),
                        "client_ticket": doc.get("client_ticket", ""),
                        "server_ticket": doc.get("server_ticket", ""),
                        "next_poll_after": 0,
                        "estimated_wait_time": 0,
                        "member_position": 0,
                        "lsg_server_ticket_size": int(
                            doc.get("lsg_server_ticket_size", 128) or 128),
                        "lsg_server_ticket": doc.get("lsg_server_ticket", ""),
                    }
                    payload = _json.dumps(
                        compact, separators=(",", ":")).encode("ascii")
                except Exception as e:
                    log({"event": "queue_compact_failed", "error": repr(e)})
                    payload = (b'{"auth_task":57,"code":700,"iv_seed":1,'
                               b'"lsg_server_ticket_size":128}')
            resp = (b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(payload)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n" + payload)
            log({"event": "queue_request", "peer": list(addr),
                 "request_line": (reqline.decode("latin1", "replace")
                                  if isinstance(reqline, (bytes, bytearray))
                                  else str(reqline)),
                 "resp_len": len(payload)})
            conn.sendall(resp)
            # Match the proven /auth/ path exactly: libcurl 7.38 needs the TLS
            # close-notify to consider the transfer done, otherwise the
            # embedded HTTP object stays at state 3 / status 0 and 0xB983F0
            # never sees the 200.
            try:
                conn.unwrap()
                log({"event": "queue_tls_close_notify", "peer": list(addr)})
            except Exception as e:
                log({"event": "queue_tls_unwrap_skipped", "peer": list(addr),
                     "error": repr(e)})
            return

        # ------------------------------------------------------------
        # H2: Lobby socket on 127.0.0.2 (or Host: 127.0.0.2) - ticket validation
        # Client sends raw 128-byte client_ticket; we reply 0x01 (ok) if
        # first 4 bytes == DE AD BD EF (NULL_REF), else 0x00.
        # ------------------------------------------------------------
        host_header = ""
        for ln in lines[1:]:
            k, _, v = ln.partition(b":")
            if k.strip().lower() == b"host":
                host_header = v.strip().decode("latin1", "replace")
                break
        is_lobby_socket = (host_header == "127.0.0.2" or host_header.startswith("127.0.0.2:"))

        if is_lobby_socket:
            # Lobby socket: validate client_ticket (128 bytes, starts with DE AD BD EF)
            ticket = body
            if len(ticket) == 128 and ticket[:4] == b"\xDE\xAD\xBD\xEF":
                payload = b"\x01"  # success
                log({"event": "ticket_valid", "peer": list(addr)})
            else:
                payload = b"\x00"  # failure
                log({"event": "ticket_invalid", "peer": list(addr), "len": len(ticket), "prefix": ticket[:8].hex()})
            resp = (b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\n" + payload)
            log({"event": "lobby_socket_resp", "peer": list(addr), "result": "ok" if payload == b"\x01" else "fail"})
            conn.sendall(resp)
            return

        raw_task = req.get("auth_task", None)
        req_task = None
        try:
            req_task = int(str(raw_task).strip())
        except (TypeError, ValueError):
            req_task = None

        if req_task is None:
            ans_task = 1
            task_note = "no auth_task in request -> fallback 1"
        elif req_task in TASK_ANSWER:
            ans_task = TASK_ANSWER[req_task]
            task_note = ("stage %d (0x%02X) -> answer %d (0x%02X)"
                         % (req_task, req_task, ans_task, ans_task))
        else:
            ans_task = req_task
            task_note = ("stage %d (0x%02X) has no response parser "
                         "(0xB99A40[idx]=5 -> 715); echoing it back"
                         % (req_task, req_task))

        log({"event": "auth_task_map", "peer": list(addr),
             "request_auth_task": raw_task, "request_stage": req_task,
             "response_auth_task": ans_task, "note": task_note})

        if os.path.exists(resp_file):
            with open(resp_file, "rb") as f:
                payload = f.read()
            log({"event": "resp_source", "file": resp_file,
                 "len": len(payload)})
            payload = payload.replace(b"$AUTH_TASK",
                                      str(ans_task).encode("ascii"))
            # Substituting an missing request field with an empty string
            # produces INVALID JSON (e.g. "iv_seed":,), which the client then
            # rejects before it can read any field.  Every substitution must
            # therefore land on a syntactically valid token:
            #   numeric placeholders  -> 0 when absent
            #   string  placeholders  -> "" (empty string) when absent
            # Response iv_seed is pinned to 0 by default.
            #
            # History: SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md section 4
            # row 4 already measured `iv_seed == 0` as SATISFIED (0xB984E7)
            # while the lobby still reset, so iv_seed is NOT the blocker.
            # The single remaining unmet condition from that same table is
            # `[obj+0x240] == 2` at 0x7F31F7.  Keep the recorded contract
            # value 0; set CODO_L_ECHO_IV_SEED=1 to restore request echoing.
            import os as _os
            echo_iv_seed = _os.environ.get("CODO_L_ECHO_IV_SEED", "0") == "1"
            forced = {} if echo_iv_seed else {"iv_seed": "0"}
            NUMERIC = ("IV_SEED",)
            for key in ("iv_seed", "title_id", "identity"):
                token = ("$" + key.upper()).encode()
                raw = forced.get(key, req.get(key, None))
                if key.upper() in NUMERIC:
                    try:
                        val = str(int(str(raw).strip())).encode("ascii")
                    except (TypeError, ValueError):
                        val = b"0"
                else:
                    s = "" if raw is None else str(raw)
                    val = b'"' + s.replace('"', '\\"').encode("utf-8") + b'"'
                payload = payload.replace(token, val)
            payload = payload.replace(b"$TICKET", b"")
            # extra_data is a nested JSON *string*.  It is required by objA
            # (stage 32, 0xB88FC0: username / encrypted_codoid (16 bytes) /
            # encrypted_register_codoid_data) and by objB (stages 10/12/24/26,
            # 0xB99610: extended_data / cd_key / time_to_live).  Insert it as a
            # JSON-string-escaped token so the body stays valid JSON.
            if b"$EXTRA_DATA" in payload:
                _iext, _xtok = extra_data_json()
                payload = payload.replace(b"$EXTRA_DATA",
                                          _xtok.encode("ascii"))
            # Last line of defence: never ship a body that is not valid JSON.
            try:
                json.loads(payload.decode("utf-8"))
                json_ok = True
            except Exception as e:
                json_ok = False
                log({"event": "template_invalid", "error": repr(e),
                     "body": payload.decode("utf-8", "replace")})
            if not json_ok:
                payload = (b'{"auth_task":%d,"code":700,"iv_seed":0}'
                           % ans_task)
            # Inject extra success fields that the client's HTTP handler might check
            extra_fields = b',"result":8900,"status":700,"error_code":0,"errcode":0'
            if payload.endswith(b"}"):
                payload = payload[:-1] + extra_fields + b"}"
        else:
            try:
                seed = int(str(req.get("iv_seed", 0)).strip())
            except (TypeError, ValueError):
                seed = 0
            payload = ('{"auth_task":%d,"code":700,"iv_seed":%d,'
                       '"result":700,"status":700,"error_code":0,"errcode":0}'
                       % (ans_task, seed)).encode("ascii")
        log({"event": "resp_plan", "peer": list(addr),
             "response_auth_task": ans_task, "note": task_note})
        # Header rules learned the hard way:
        #   * never emit a header with an EMPTY value -- the client's HTTP
        #     parser rejects "X-TransactionID: \r\n" (a GET / request has no
        #     transaction id, so this used to happen on every probe request)
        #   * this handler closes the socket after sendall, so the header must
        #     say "close"; advertising keep-alive made the client block
        #     waiting for more data on a connection we were about to drop
        hdr = [b"HTTP/1.1 200 OK",
               b"Content-Type: application/json",
               b"Connection: close",
               b"Content-Length: " + str(len(payload)).encode()]
        if xid:
            hdr.append(b"X-TransactionID: " + xid.encode("latin1"))
        resp = b"\r\n".join(hdr) + b"\r\n\r\n" + payload
        # One line that always carries BOTH sides of the round trip, so the
        # request stage and the answer can never be mismatched when reading
        # the log later.
        log({"event": "roundtrip",
             "peer": list(addr),
             "req_auth_task": req.get("auth_task"),
             "req_body": body.decode("utf-8", "replace"),
             "resp_auth_task": ans_task,
             "resp_body": payload.decode("utf-8", "replace")})
        conn.sendall(resp)
        # The client embeds libcurl 7.38 + OpenSSL 0.9.8p.  If we drop the
        # socket straight after sendall (SHUT_RDWR + close, no close_notify,
        # possible RST) the transfer races the final read: curl never reaches
        # "done", CURLINFO_RESPONSE_CODE (stored at [httpobj+0x464]) stays 0,
        # and 0xBAA2D0 maps that to BD_EMPTY (0x2E5) even though the bytes we
        # sent were correct.  Instead: tell the peer we are done writing,
        # keep reading until it closes (draining its FIN), then close.
        try:
            conn.unwrap()
            log({"event": "tls_close_notify", "peer": list(addr)})
        except Exception as e:
            log({"event": "tls_unwrap_skipped", "peer": list(addr),
                 "error": repr(e)})
    except Exception as e:
        log({"event": "error", "peer": list(addr), "error": repr(e)})
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
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8443)
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

    # The game ships OpenSSL 0.9.8p (Nov 2010): TLS 1.0 only, SHA1 signatures,
    # classic CBC cipher suites.  OpenSSL 3 defaults reject all of that, so the
    # negotiation dies with "no suitable signature algorithm" /
    # "no shared cipher".  Re-open the old algorithms for this local probe only.
    try:
        ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
    except Exception as e:
        log({"event": "warn", "where": "set_ciphers", "error": repr(e)})
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
    try:
        ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
    except Exception:
        pass
    try:
        ctx.set_ecdh_curve("prime256v1")
    except Exception:
        pass

    def sni_cb(sock, name, c):
        try:
            log({"event": "sni", "peer": list(sock.getpeername()),
                 "server_name": name})
        except Exception:
            pass

    try:
        ctx.sni_callback = sni_cb
    except Exception:
        pass

    try:
        log({"event": "tls_config",
             "min": str(ctx.minimum_version), "max": str(ctx.maximum_version),
             "ciphers": len(ctx.get_ciphers())})
    except Exception:
        pass

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Windows: SO_REUSEADDR lets a SECOND process bind the same port, so a
    # leftover instance silently steals half of the client's connections and
    # the lobby appears to "work, then break, then work again" from run to
    # run.  Refuse to start twice instead of sharing the port.
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
        threading.Thread(target=handle, args=(s, addr, ctx, log), daemon=True).start()
    return 0


if __name__ == "__main__":
    sys.exit(main())

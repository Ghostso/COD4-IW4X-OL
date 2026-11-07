"""Regression test for the /auth/ response contract.

Starts lobby_probe_server.py on a scratch port, posts stage-shaped requests
exactly like the retail client sends them, and asserts the reply satisfies
every rule the client enforces. ASCII only.

Run:
  python -X utf8 _auth_resp_test.py
"""
import base64
import json
import os
import socket
import ssl
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 18443
BIND = "127.0.0.1"
LOG = os.path.join(HERE, "_auth_resp_test.jsonl")

TASK_ANSWER = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 33}
NULL_REF = 0xEFBDADDE


def post(body_obj, timeout=3.0):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
    except Exception:
        pass
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except Exception:
        pass
    raw = json.dumps(body_obj).encode("utf-8")
    s = socket.create_connection((BIND, PORT), timeout=timeout)
    try:
        c = ctx.wrap_socket(s, server_hostname=BIND)
        req = (b"POST /auth/ HTTP/1.1\r\n"
               b"Host: " + BIND.encode() + b":" + str(PORT).encode() + b"\r\n"
               b"Accept: */*\r\nContent-Type: application/json\r\n"
               b"X-TransactionID: 1\r\n"
               b"Content-Length: " + str(len(raw)).encode() + b"\r\n"
               b"Connection: close\r\n\r\n" + raw)
        c.sendall(req)
        buf = b""
        while True:
            try:
                chunk = c.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
        return buf
    finally:
        try:
            s.close()
        except Exception:
            pass


def parse(buf):
    head, _, body = buf.partition(b"\r\n\r\n")
    status = head.split(b"\r\n")[0].decode("latin1")
    return status, body


def check(label, cond, extra=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", label,
                           ("  " + extra) if extra and not cond else ""))
    return bool(cond)


def main():
    exe = os.path.join(HERE, "lobby_probe_server.py")
    if os.path.exists(LOG):
        os.remove(LOG)
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-u", exe,
         "--cert-dir", HERE, "--bind", BIND, "--port", str(PORT),
         "--log", LOG],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    all_ok = True
    try:
        time.sleep(2.5)
        if proc.poll() is not None:
            print("server died on startup, exit=%s" % proc.returncode)
            return 1

        cases = [10, 0, 12, 24, 26, 32, 7]
        for stage in cases:
            req = {"auth_task": str(stage), "iv_seed": "3371511186",
                   "title_id": "0", "identity": "356c4bc3"}
            try:
                buf = post(req)
            except Exception as e:
                print("stage %-3d -> request error %r" % (stage, e))
                all_ok = False
                continue
            status, body = parse(buf)
            print("stage %-3d %s" % (stage, status))
            all_ok &= check("HTTP 200", status.endswith("200 OK"))
            try:
                doc = json.loads(body.decode("utf-8"))
            except Exception as e:
                all_ok &= check("body is JSON", False, repr(e))
                continue

            want = TASK_ANSWER.get(stage, stage)
            all_ok &= check("auth_task == %d (got %r)"
                            % (want, doc.get("auth_task")),
                            doc.get("auth_task") == want)
            all_ok &= check("code == 700", doc.get("code") == 700)
            all_ok &= check("iv_seed present", "iv_seed" in doc)

            if stage == 0:
                print("  (stage 0 uses 0xB991A0: auth_task/code only)")
                continue

            for name in ("client_ticket", "server_ticket"):
                has = name in doc
                all_ok &= check(name + " present", has)
                if not has:
                    continue
                try:
                    dec = base64.b64decode(doc[name])
                except Exception as e:
                    all_ok &= check(name + " base64", False, repr(e))
                    continue
                all_ok &= check("%s decodes to 128 bytes (got %d)"
                                % (name, len(dec)), len(dec) == 128)
                if name == "client_ticket":
                    tag = int.from_bytes(dec[:4], "little")
                    all_ok &= check(
                        "client_ticket tag == 0x%08X (got 0x%08X)"
                        % (NULL_REF, tag), tag == NULL_REF)
        print()
        print("RESULT: " + ("ALL PASS" if all_ok else "FAILURES PRESENT"))
        return 0 if all_ok else 1
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            print()
            print("--- auth_task_map events from server log ---")
            with open(LOG, encoding="utf-8", errors="replace") as f:
                for ln in f:
                    if "auth_task_map" in ln or "resp_plan" in ln:
                        print(ln.rstrip())
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""CODOL /auth/ TLS server + raw logging, SHA-1 chain, SECLEVEL=0 first."""
import socket, ssl, threading, time, os, sys

D = r"CODOLServer\logs\z7fix"
os.makedirs(D, exist_ok=True)
fh = open(os.path.join(D, "auth_sha1.log"), "w", encoding="utf-8")
def w(m):
    print(m, flush=True); fh.write(m+"\n"); fh.flush()

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# IMPORTANT: seclevel must be lowered BEFORE loading the SHA-1 signed chain,
# otherwise OpenSSL 3 raises CA_MD_TOO_WEAK.
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
ctx.verify_mode = ssl.CERT_NONE
ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                    r"CODOLServer\lobby_server\lobby_server.key")
w("TLS context ready (SHA-1 chain, SECLEVEL=0)")

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1", 8443)); srv.listen(8)
w("=== listening 127.0.0.1:8443 ===")

def handle(c, a):
    w("=== conn %s:%d ===" % a)
    try:
        c.settimeout(12)
        s = ctx.wrap_socket(c, server_side=True)
        w("  TLS OK  cipher=%s ver=%s" % (s.cipher(), s.version()))
        s.settimeout(12)
        req = b""
        while b"\r\n\r\n" not in req and len(req) < 200000:
            try:
                d = s.recv(8192)
            except socket.timeout:
                break
            if not d: break
            req += d
        w("  request %d bytes" % len(req))
        head = req.split(b"\r\n\r\n",1)[0].decode("latin1","replace")
        w("  --- HTTP head ---")
        for line in head.splitlines()[:30]:
            w("    " + line)
        body = req.split(b"\r\n\r\n",1)[1] if b"\r\n\r\n" in req else b""
        w("  --- body (%d bytes) ---" % len(body))
        w("    " + repr(body[:600]))
        # reply
        resp_body = b'{"ret":0,"task":11,"auth_task":11,"replyId":1}'
        hdr = ("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
               "Content-Length: %d\r\nConnection: close\r\n\r\n" % len(resp_body))
        s.sendall(hdr.encode() + resp_body)
        w("  --> 200 (%d bytes)" % len(resp_body))
        try: s.unwrap()
        except Exception: pass
    except ssl.SSLError as e:
        w("  SSL ERROR: %s" % e)
    except Exception as e:
        w("  ERROR: %r" % e)
    finally:
        try: c.close()
        except Exception: pass

t0 = time.time()
while time.time() - t0 < 170:
    srv.settimeout(5)
    try:
        c, a = srv.accept()
    except socket.timeout:
        continue
    threading.Thread(target=handle, args=(c,a), daemon=True).start()
w("done")

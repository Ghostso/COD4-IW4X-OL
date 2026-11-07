# -*- coding: utf-8 -*-
"""TLS server that logs EVERY byte from the client, so we see exactly what it
sends after receiving our Certificate."""
import socket, ssl, threading, time, os, struct

D = r"CODOLServer\logs\z7fix"
os.makedirs(D, exist_ok=True)
LOG = os.path.join(D, "tlsdetail.log")
fh = open(LOG, "w", encoding="utf-8")
def w(m):
    print(m, flush=True); fh.write(m+"\n"); fh.flush()

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                    r"CODOLServer\lobby_server\lobby_server.key")
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
ctx.verify_mode = ssl.CERT_NONE

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1",8443)); srv.listen(4)
w("listening 8443 (TLS, logging raw)")

def handle(c, a):
    w("=== conn %s:%d ===" % a)
    c.settimeout(8)
    raw = b""
    try:
        s = ctx.wrap_socket(c, server_side=True)
        w("  HANDSHAKE OK cipher=%s ver=%s" % (s.cipher(), s.version()))
        while True:
            d = s.recv(4096)
            if not d: break
            raw += d
            if len(raw) > 100000: break
        w("  app data %d bytes" % len(raw))
        w("  hex: " + " ".join("%02X"%x for x in raw[:200]))
        try: w("  text: " + repr(raw[:300]))
        except Exception: pass
    except ssl.SSLError as e:
        w("  SSL ERROR: %s" % e)
    except Exception as e:
        w("  ERROR: %r" % e)
    finally:
        try: c.close()
        except Exception: pass

t0 = time.time()
while time.time()-t0 < 160:
    srv.settimeout(5)
    try:
        c, a = srv.accept()
    except socket.timeout:
        continue
    threading.Thread(target=handle, args=(c,a), daemon=True).start()
w("done")

# -*- coding: utf-8 -*-
"""Raw TCP listener on 8443 that records the client's first bytes verbatim."""
import socket, time, os, threading

LOG = r"CODOLServer\logs\z7fix\raw8443.bin"
os.makedirs(os.path.dirname(LOG), exist_ok=True)
HOST, PORT = "127.0.0.1", 8443

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((HOST, PORT))
srv.listen(4)
print("raw listener on %s:%d  (recording to %s)" % (HOST, PORT, LOG), flush=True)

fh = open(os.path.join(os.path.dirname(LOG), "raw8443.log"), "w", encoding="utf-8")
def w(m):
    print(m, flush=True); fh.write(m+"\n"); fh.flush()

def handle(c, a):
    w("=== conn from %s:%d ===" % a)
    c.settimeout(6.0)
    allb = b""
    try:
        while len(allb) < 65536:
            d = c.recv(4096)
            if not d: break
            allb += d
            if len(allb) >= 16 and not allb.startswith(b"\x16\x03"):
                break
    except socket.timeout:
        pass
    except Exception as e:
        w("  recv err: %r" % e)
    blob = os.path.join(os.path.dirname(LOG), "raw8443_%d.bin" % int(a[1]))
    open(blob, "wb").write(allb)
    w("  got %d bytes -> %s" % (len(allb), blob))
    w("  hex: " + " ".join("%02X" % x for x in allb[:64]))
    w("  ascii: " + repr(allb[:64]))
    try: c.close()
    except Exception: pass

t0 = time.time()
while time.time() - t0 < 150:
    srv.settimeout(5.0)
    try:
        c, a = srv.accept()
    except socket.timeout:
        continue
    threading.Thread(target=handle, args=(c,a), daemon=True).start()
w("listener done")

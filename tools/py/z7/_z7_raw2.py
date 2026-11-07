# -*- coding: utf-8 -*-
"""Raw listener that reads COMPLETE TLS records."""
import socket, time, os, threading, struct

D = r"CODOLServer\logs\z7fix"
os.makedirs(D, exist_ok=True)
LOG = os.path.join(D, "raw2.log")
fh = open(LOG, "w", encoding="utf-8")
def w(m):
    print(m, flush=True); fh.write(m+"\n"); fh.flush()

def recvn(c, n, timeout=6.0):
    c.settimeout(timeout)
    buf = b""
    while len(buf) < n:
        d = c.recv(n - len(buf))
        if not d: break
        buf += d
    return buf

def handle(c, a):
    w("=== conn from %s:%d ===" % a)
    try:
        hdr = recvn(c, 5)
        if len(hdr) < 5:
            w("  short header: %r" % hdr); return
        ctype, ver, ln = hdr[0], hdr[1:3], struct.unpack(">H", hdr[3:5])[0]
        rec = recvn(c, ln)
        full = hdr + rec
        w("  record: type=0x%02X ver=%s len=%d total=%d" % (ctype, ver.hex(), ln, len(full)))
        p = os.path.join(D, "clihello_%d.bin" % a[1])
        open(p, "wb").write(full)
        w("  saved -> %s" % p)
        w("  hex: " + " ".join("%02X" % x for x in full))
        # parse ClientHello
        if ctype == 0x16 and full[5] == 0x01:
            b = full[9:]
            b = b[2+32:]              # version + random
            sidl = b[0]; b = b[1+sidl:]
            csl = struct.unpack(">H", b[:2])[0]; b = b[2:]
            suites = [struct.unpack(">H", b[i:i+2])[0] for i in range(0, csl, 2)]
            b = b[csl:]
            w("  cipher suites (%d): %s" % (len(suites), " ".join("0x%04X"%s for s in suites)))
            compl = b[0]; b = b[1:]
            w("  compression (%d): %s" % (compl, " ".join("%02X"%x for x in b[:compl])))
            b = b[compl:]
            if len(b) >= 2:
                extl = struct.unpack(">H", b[:2])[0]; b = b[2:]
                w("  extensions len=%d" % extl)
                i = 0
                while i + 4 <= len(b) and i < extl:
                    et, el = struct.unpack(">HH", b[i:i+4])
                    w("     ext 0x%04X len=%d" % (et, el))
                    i += 4 + el
            else:
                w("  extensions: (none present)")
    except Exception as e:
        w("  ERR %r" % e)
    finally:
        try: c.close()
        except Exception: pass

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 8443)); srv.listen(4)
w("listening 127.0.0.1:8443")
t0 = time.time()
while time.time() - t0 < 160:
    srv.settimeout(5)
    try:
        c, a = srv.accept()
    except socket.timeout:
        continue
    threading.Thread(target=handle, args=(c,a), daemon=True).start()
w("done")

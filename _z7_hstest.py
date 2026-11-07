# -*- coding: utf-8 -*-
"""Reproduce the client's exact ClientHello against our TLS server and see
what the server negotiates."""
import socket, ssl, threading, time, subprocess, os

# The exact 70 bytes we captured from the client
CH = bytes.fromhex(
 "16 03 01 00 41 01 00 00 3D 03 01 6A C0 8E E1 19 5C 9F 64 76 2F 1E 55 DF C5 6D F2 6E "
 "B9 33 D0 B7 CD 8A F2 B7 D1 39 44 F4 B7 C0 3B 00 00 16 00 39 00 38 00 35 00 33 00 32 "
 "00 2F 00 16 00 13 00 0A")
print("clienthello bytes:", len(CH))

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                    r"CODOLServer\lobby_server\lobby_server.key")
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
ctx.verify_mode = ssl.CERT_NONE

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1", 18443)); srv.listen(1)
res = {}
def worker():
    try:
        c,a = srv.accept()
        c.settimeout(5)
        d = c.recv(4096)
        res["serverhello"] = d
        try:
            s = ctx.wrap_socket(c, server_side=True)
            res["ok"] = True
            res["cipher"] = s.cipher()
            res["version"] = s.version()
        except Exception as e:
            res["err"] = repr(e)
    except Exception as e:
        res["accept_err"] = repr(e)

threading.Thread(target=worker, daemon=True).start()
time.sleep(0.4)

cli = socket.create_connection(("127.0.0.1", 18443), timeout=5)
cli.sendall(CH)
time.sleep(1.5)
try:
    sh = cli.recv(4096)
    res.setdefault("client_saw", sh)
except Exception as e:
    res["client_recv_err"] = repr(e)
cli.close(); srv.close(); time.sleep(0.5)

print("\n=== server reply to ClientHello ===")
sh = res.get("serverhello")
if sh: print("  ", " ".join("%02X"%x for x in sh[:80]))
print("\n=== handshake result ===")
print("  ok:", res.get("ok"))
print("  cipher:", res.get("cipher"))
print("  version:", res.get("version"))
print("  err:", res.get("err"))
print("  accept_err:", res.get("accept_err"))

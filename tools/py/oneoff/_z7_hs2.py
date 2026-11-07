# -*- coding: utf-8 -*-
"""Full 70-byte ClientHello -> our TLS server. Record the server's raw reply."""
import socket, ssl, threading, time, os

RAW = open(r"CODOLServer\logs\z7fix\clihello_57389.bin","rb").read()
print("ClientHello:", len(RAW), "bytes")

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                    r"CODOLServer\lobby_server\lobby_server.key")
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
ctx.verify_mode = ssl.CERT_NONE

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0)); srv.listen(1)
port = srv.getsockname()[1]
res = {}
def worker():
    try:
        c, a = srv.accept(); c.settimeout(5)
        s = ctx.wrap_socket(c, server_side=True)
        res["cipher"] = s.cipher(); res["ver"] = s.version()
        try:
            d = s.recv(4096); res["appdata"] = d
        except Exception as e:
            res["recv_err"] = repr(e)
    except Exception as e:
        res["err"] = type(e).__name__ + ": " + str(e)[:120]
threading.Thread(target=worker, daemon=True).start()
time.sleep(0.3)

cli = socket.create_connection(("127.0.0.1", port), timeout=6)
cli.sendall(RAW)
time.sleep(0.3)
try:
    reply = cli.recv(4096)
    print("\nserver reply (%d bytes):" % len(reply))
    print("  ", " ".join("%02X"%x for x in reply[:64]))
    if reply and reply[0] == 0x15:
        print("  -> ALERT")
        print("     level=%d desc=%d" % (reply[5], reply[6]) if len(reply)>6 else "")
except Exception as e:
    print("client recv err:", e)
time.sleep(2.0)
cli.close(); srv.close(); time.sleep(0.3)
print("\nresult:")
print("  cipher :", res.get("cipher"))
print("  version:", res.get("ver"))
print("  err    :", res.get("err"))
print("  appdata:", res.get("appdata"))

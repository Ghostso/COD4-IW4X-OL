# -*- coding: utf-8 -*-
"""Decode the server's ServerHello to see the chosen cipher, and keep the
connection longer to observe what follows."""
import socket, ssl, threading, time, struct

RAW = open(r"CODOLServer\logs\z7fix\clihello_57389.bin","rb").read()

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

def worker():
    c, a = srv.accept(); c.settimeout(6)
    try:
        s = ctx.wrap_socket(c, server_side=True)
        print("server: handshake OK", s.cipher(), s.version())
    except Exception as e:
        print("server: handshake FAILED:", type(e).__name__, str(e)[:150])
threading.Thread(target=worker, daemon=True).start()
time.sleep(0.3)

cli = socket.create_connection(("127.0.0.1", port), timeout=8)
cli.sendall(RAW)
time.sleep(0.5)
cli.settimeout(3.0)
alld = b""
try:
    while True:
        d = cli.recv(4096)
        if not d: break
        alld += d
except Exception:
    pass
print("\nserver sent %d bytes total" % len(alld))
# parse first record = ServerHello
if len(alld) > 11 and alld[5] == 0x02:
    body = alld[9:]
    ver = body[0:2]
    p = 2 + 32
    sidl = body[p]; p += 1 + sidl
    cs = struct.unpack(">H", body[p:p+2])[0]
    comp = body[p+2]
    print("  ServerHello: ver=%s  session_id_len=%d  cipher=0x%04X  compression=%02X"
          % (ver.hex(), sidl, cs, comp))
    NAMES = {0x35:"AES256-SHA",0x2F:"AES128-SHA",0x39:"DHE-RSA-AES256-SHA",
             0x33:"DHE-RSA-AES128-SHA",0x0A:"DES-CBC3-SHA",0x05:"RC4-SHA",
             0x04:"RC4-MD5",0x2F:"AES128-SHA"}
    print("  -> negotiated:", NAMES.get(cs, "?"))
print("\n  first 120 bytes:", " ".join("%02X"%x for x in alld[:120]))
time.sleep(1)
cli.close(); srv.close()

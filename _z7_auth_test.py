# -*- coding: utf-8 -*-
import socket, ssl, json, os, hashlib, warnings
warnings.filterwarnings("ignore")
CA = os.path.join("CODOLServer","lobby_server","lobby_ca.pem")
HOST = "formal-zone-auth.codol.qq.com"   # must resolve to 127.0.0.1
PORT = 3074

body = json.dumps({"auth_task":"10","iv_seed":"3371511186","title_id":"0","identity":"356c4bc3"}).encode()

print("=== STRICT VERIFY (server_hostname=%s) ===" % HOST)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = True
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.load_verify_locations(CA)
try:
    ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
except Exception: pass
try:
    ctx.minimum_version = ssl.TLSVersion.TLSv1
except Exception: pass

try:
    s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
    c = ctx.wrap_socket(s, server_hostname=HOST)
    print("TLS OK  version=", c.version(), "cipher=", c.cipher()[0])
    cert = c.getpeercert()
    print("peer subject:", cert.get("subject"))
    print("peer SAN    :", cert.get("subjectAltName"))
    req = (b"POST /auth/ HTTP/1.1\r\n"
           b"Host: " + HOST.encode() + b":" + str(PORT).encode() + b"\r\n"
           b"Accept: */*\r\nContent-Type: application/json\r\n"
           b"X-TransactionID: 1\r\n"
           b"Content-Length: " + str(len(body)).encode() + b"\r\n"
           b"Connection: close\r\n\r\n" + body)
    c.sendall(req)
    buf = b""
    while True:
        try:
            ch = c.recv(8192)
        except socket.timeout:
            break
        if not ch: break
        buf += ch
    head, _, bd = buf.partition(b"\r\n\r\n")
    print("STATUS:", head.split(b"\r\n")[0].decode("latin1"))
    print("BODY  :", bd.decode("utf-8","replace")[:800])
    c.close()
except Exception as e:
    print("FAIL:", type(e).__name__, e)

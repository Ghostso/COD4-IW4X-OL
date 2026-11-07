import socket, ssl, json, sys, os

ca_path = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923\cacert.pem"

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.set_ciphers("ALL:@SECLEVEL=0")
ctx.load_verify_locations(ca_path)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_REQUIRED

sock = socket.create_connection(("127.0.0.1", 443), timeout=10)
ssock = ctx.wrap_socket(sock, server_hostname="127.0.0.1")
print("TLS version:", ssock.version())

# GET /
req = b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
ssock.sendall(req)
resp = b""
while True:
    chunk = ssock.recv(4096)
    if not chunk:
        break
    resp += chunk
print("GET response:\n", resp.decode(errors="replace"))

# POST /auth/
auth_req = {"auth_task": 0}
body = json.dumps(auth_req).encode()
req2 = (
    b"POST /auth/ HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nContent-Length: "
    + str(len(body)).encode()
    + b"\r\nConnection: close\r\n\r\n"
    + body
)
ssock.sendall(req2)
resp2 = b""
while True:
    chunk = ssock.recv(4096)
    if not chunk:
        break
    resp2 += chunk
print("POST /auth/ response:\n", resp2.decode(errors="replace"))

ssock.close()
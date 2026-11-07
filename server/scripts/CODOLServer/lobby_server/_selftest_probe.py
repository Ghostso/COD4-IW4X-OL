"""Local /auth/ self-test: proves the probe answers and logs a roundtrip line.
ASCII only. Usage: python -X utf8 _selftest_probe.py <port> [stage]
"""
import json
import socket
import ssl
import sys

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8843
stage = str(sys.argv[3]) if len(sys.argv) > 3 else "10"

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1
ctx.set_ciphers("ALL:@SECLEVEL=0")

req = {
    "auth_task": stage,
    "iv_seed": "12345",
    "title_id": "0",
    "identity": "356c4bc3",
    "extra_data": '{"version": "0"}',
}
body = json.dumps(req).encode("utf-8")

s = ctx.wrap_socket(socket.create_connection((host, port), timeout=8))
head = (
    b"POST /auth/ HTTP/1.1\r\n"
    b"Host: 127.0.0.1:" + str(port).encode() + b"\r\n"
    b"Accept: */*\r\n"
    b"X-Selftest: 1\r\n"
    b"Content-Type: application/json\r\n"
    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
    b"\r\n"
)
s.sendall(head + body)
data = b""
while b"\r\n\r\n" not in data:
    chunk = s.recv(4096)
    if not chunk:
        break
    data += chunk
h, _, rest = data.partition(b"\r\n\r\n")
print("TLS   :", s.version(), s.cipher()[0])
print("HEAD  :", h.decode("latin1"))
print("BODY  :", rest.decode("utf-8", "replace"))
s.close()

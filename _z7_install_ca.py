# -*- coding: utf-8 -*-
"""Install the CODOL local CA: (a) LocalMachine\\Root, (b) append to cacert.pem."""
import json, os, socket

STAGE = r"D:\z7tmp"
os.makedirs(STAGE, exist_ok=True)
CA = os.path.join(os.getcwd(), "CODOLServer", "lobby3074", "codol_ca.pem")
print("CA:", CA, os.path.isfile(CA))
print(open(CA, encoding="utf-8").read()[:80].replace("\n", " | "))

helper = r'''
import os, subprocess
CA = r"%s"
# (a) install into LocalMachine Root
r = subprocess.run(["certutil", "-addstore", "-f", "Root", CA],
                   capture_output=True)
print("certutil rc:", r.returncode)
out = (r.stdout + r.stderr).decode("gbk", "replace")
print(out.strip()[-500:])
# verify
r2 = subprocess.run(["certutil", "-store", "Root"], capture_output=True)
s = r2.stdout.decode("gbk", "replace")
print("in Root store:", "CODOL-LOCAL" in s)
''' % CA

hp = os.path.join(STAGE, "install_ca.py")
open(hp, "wb").write(helper.replace("\n","\r\n").encode("ascii"))
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
req = {"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
buf=b""
while not buf.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    buf+=c
r=json.loads(buf.decode("utf-8"))
print("rc:",r.get("rc"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:400])

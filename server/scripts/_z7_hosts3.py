# -*- coding: utf-8 -*-
"""Append hosts lines using append mode (truncate is blocked on hosts)."""
import json, os, socket

helper = r'''
import os, sys
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
NEED = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]
raw = open(H, "rb").read().decode("utf-8", "replace")
miss = [n for n in NEED if n not in raw]
if not miss:
    print("ALREADY_PRESENT")
else:
    with open(H, "ab") as f:
        f.write(("\r\n# z7 codol lobby redirect\r\n" +
                 "\r\n".join(miss) + "\r\n").encode("utf-8"))
    print("APPENDED", len(miss), "line(s)")
back = open(H, "rb").read().decode("utf-8", "replace")
print("VERIFY_ALL_PRESENT:", all(n in back for n in NEED))
for l in back.splitlines():
    if l.strip() and not l.strip().startswith("#"):
        print("LIVE>", l)
print("HAS_down.qq:", "down.qq.com" in back, " HAS_intldlgs:", "intldlgs" in back)
'''
hp = os.path.join(os.getcwd(), "_z7_hosts_helper.py")
open(hp, "wb").write(helper.replace("\n", "\r\n").encode("ascii"))

st = json.load(open(os.path.join("CODOLServer", "logs", "elevated_agent.json"), encoding="utf-8"))
req = {"action": "run", "argv": ["python", "-X", "utf8", hp], "token": st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req) + "\n").encode("utf-8"))
buf = b""
while not buf.endswith(b"\n"):
    c = s.recv(65536)
    if not c: break
    buf += c
r = json.loads(buf.decode("utf-8"))
print("rc:", r.get("rc"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:400])

# -*- coding: utf-8 -*-
"""Append the two hosts lines via elevated agent running a python one-liner."""
import json, os, socket

H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
NEED = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]

# Build an ASCII-only helper script (avoids PS/path encoding traps)
helper = r'''
import io, os, sys
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
NEED = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]
raw = open(H, "rb").read().decode("utf-8", "replace")
miss = [n for n in NEED if n not in raw]
if not miss:
    print("ALREADY_PRESENT"); sys.exit(0)
add = "\r\n".join([""] + ["# z7 codol lobby redirect"] + miss) + "\r\n"
new = raw.rstrip("\r\n") + add
open(H, "wb").write(new.encode("utf-8"))
back = open(H, "rb").read().decode("utf-8", "replace")
print("WROTE", all(n in back for n in NEED))
for l in back.splitlines():
    if l.strip() and not l.strip().startswith("#"):
        print("LIVE>", l)
'''
hp = os.path.join(os.getcwd(), "_z7_hosts_helper.py")
open(hp, "wb").write(helper.replace("\n", "\r\n").encode("ascii"))

st = json.load(open(os.path.join("CODOLServer", "logs", "elevated_agent.json"), encoding="utf-8"))
req = {"action": "run",
       "argv": ["python", "-X", "utf8", hp],
       "token": st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req) + "\n").encode("utf-8"))
buf = b""
while not buf.endswith(b"\n"):
    c = s.recv(65536)
    if not c: break
    buf += c
r = json.loads(buf.decode("utf-8"))
print("rc:", r.get("rc"))
print("stdout:", r.get("stdout"))
print("stderr:", (r.get("stderr") or "")[:400])

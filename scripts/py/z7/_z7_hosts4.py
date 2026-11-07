# -*- coding: utf-8 -*-
"""Write hosts via copy-over (the method that worked historically)."""
import json, os, socket, shutil

# 1. build the desired hosts content locally (non-elevated, in our workspace)
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
raw = open(H, "rb").read().decode("utf-8", "replace")
lines = [l for l in raw.splitlines() if "codol.qq.com" not in l]
lines.append("")
lines.append("# --- CODOL local lobby (added 2026-10-03) ---")
lines.append("127.0.0.1 formal-zone-auth.codol.qq.com")
lines.append("127.0.0.2 formal-zone-lsg.codol.qq.com")
out = "\r\n".join(lines).rstrip() + "\r\n"

staged = os.path.join(os.getcwd(), "_z7_hosts_staged.txt")
open(staged, "wb").write(out.encode("utf-8"))
print("staged %d bytes -> %s" % (len(out.encode()), staged))

# 2. elevated copy over
helper = r'''
import os, shutil, sys
src = r"%s"
dst = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
shutil.copy2(src, dst)
back = open(dst, "rb").read().decode("utf-8", "replace")
need = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]
print("VERIFY:", all(n in back for n in need))
for l in back.splitlines():
    if l.strip() and not l.strip().startswith("#"):
        print("LIVE>", l)
print("HAS_down.qq:", "down.qq.com" in back)
''' % staged.replace("\\", "\\\\")

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

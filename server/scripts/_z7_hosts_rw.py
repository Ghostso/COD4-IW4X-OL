# -*- coding: utf-8 -*-
"""Write hosts the correct way: open r+b, rewrite in place, truncate."""
import json, os, socket

STAGE = r"D:\z7tmp"
os.makedirs(STAGE, exist_ok=True)
helper = r'''
import os
dst = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
NEED = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]
f = open(dst, "r+b")
raw = f.read().decode("utf-8", "replace")
lines = [l for l in raw.splitlines() if "codol.qq.com" not in l]
lines.append("")
lines.append("# z7 codol local lobby")
lines.extend(NEED)
new = ("\r\n".join(lines).rstrip() + "\r\n").encode("utf-8")
f.seek(0)
f.write(new)
f.truncate()
f.close()
back = open(dst, "rb").read().decode("utf-8", "replace")
print("VERIFY_ALL:", all(n in back for n in NEED))
print("bytes:", len(back.encode()))
for l in back.splitlines():
    if l.strip() and not l.strip().startswith("#"):
        print("LIVE>", l)
print("HAS_down_qq:", "down.qq.com" in back)
print("HAS_intldlgs:", "intldlgs" in back)
'''
hp = os.path.join(STAGE, "hosts_write.py")
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
print((r.get("stderr") or "")[:300])

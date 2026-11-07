# -*- coding: utf-8 -*-
"""Probe exactly how hosts is blocked. ASCII-only helper at D:\z7tmp."""
import json, os, socket

STAGE = r"D:\z7tmp"
os.makedirs(STAGE, exist_ok=True)
helper = r'''
import os
dst = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
print("exists:", os.path.exists(dst))
print("size:", os.path.getsize(dst))
print("writable:", os.access(dst, os.W_OK))
for mode, desc in [("r","read"),("rb","read-binary"),("r+b","read-write"),
                   ("wb","truncate"),("ab","append"),("a","append-text")]:
    try:
        f = open(dst, mode); f.close()
        print("  open %-4s (%s): OK" % (mode, desc))
    except Exception as e:
        print("  open %-4s (%s): FAIL %s" % (mode, desc, e))
# try creating a sibling file in the same dir
sib = os.path.join(os.path.dirname(dst), "_z7_sib.txt")
try:
    open(sib,"w").write("t"); os.remove(sib)
    print("sibling create/delete: OK")
except Exception as e:
    print("sibling create/delete: FAIL", e)
'''
hp = os.path.join(STAGE, "probe.py")
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

# -*- coding: utf-8 -*-
"""Diagnose: can the agent subprocess write to a protected dir?"""
import json, os, socket
helper = r'''
import ctypes, os, sys
print("cwd:", os.getcwd())
print("exe:", sys.executable)
try:
    admin = ctypes.windll.shell32.IsUserAnAdmin()
except Exception as e:
    admin = "err"
print("IsUserAnAdmin:", admin)
# try writing to System32
p = os.path.join(os.environ["windir"], "System32", "_z7_writetest.txt")
try:
    open(p, "w").write("x")
    os.remove(p)
    print("System32 write: OK")
except Exception as e:
    print("System32 write: FAIL", e)
# try opening hosts for append
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
try:
    f = open(H, "a"); f.close()
    print("hosts append-open: OK")
except Exception as e:
    print("hosts append-open: FAIL", e)
'''
hp = os.path.join(os.getcwd(), "_z7_wtest.py")
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
print((r.get("stderr") or "")[:500])

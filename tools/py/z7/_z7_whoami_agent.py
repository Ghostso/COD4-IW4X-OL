# -*- coding: utf-8 -*-
import json, os, socket
helper = r'''
import ctypes, os, sys
try:
    admin = ctypes.windll.shell32.IsUserAnAdmin()
except Exception as e:
    admin = "err:%s" % e
print("IsUserAnAdmin:", admin)
print("user:", os.environ.get("USERNAME"), "domain:", os.environ.get("USERDOMAIN"))
print("elevated:", os.environ.get("__COMPAT_LAYER"))
'''
hp = os.path.join(os.getcwd(), "_z7_whoami.py")
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
print((r.get("stderr") or "")[:300])

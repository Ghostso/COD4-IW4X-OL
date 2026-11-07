# -*- coding: utf-8 -*-
import json, os, socket
helper = r'''
import subprocess
for cmd in [
    ["netsh","interface","portproxy","delete","v4tov4","listenport=443","listenaddress=127.0.0.1"],
    ["netsh","interface","portproxy","delete","v4tov4","listenport=443","listenaddress=127.0.0.2"],
]:
    r = subprocess.run(cmd, capture_output=True)
    print(" ".join(cmd[-2:]), "rc=", r.returncode)
    print("  ", (r.stdout+r.stderr).decode("gbk","replace").strip()[:200])
r = subprocess.run(["netsh","interface","portproxy","show","v4tov4"], capture_output=True)
print("--- remaining ---")
print(r.stdout.decode("gbk","replace"))
'''
STAGE = r"D:\z7tmp"
hp = os.path.join(STAGE, "del_pp.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
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

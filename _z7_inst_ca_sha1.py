import json, os, socket, shutil
STAGE = r"D:\z7tmp"
shutil.copy2(r"D:\z7tmp\cert_sha1\ca.pem", os.path.join(STAGE, "ca_sha1.pem"))
helper = r'''
import subprocess, os
CA = r"D:\z7tmp\ca_sha1.pem"
OLD = "7803584BA37D5DE0AA752B12D232D495E5712E55"
NEW = "0B846A06BAF953F00B5AA2465F39E3CB10E540FB"
print("removing old CA...")
r = subprocess.run(["certutil","-delstore","Root",OLD], capture_output=True)
print("  delstore rc=", r.returncode)
r = subprocess.run(["certutil","-addstore","-f","Root",CA], capture_output=True)
print("addstore rc=", r.returncode)
print((r.stdout+r.stderr).decode("gbk","replace").strip()[-300:])
r = subprocess.run(["certutil","-store","Root"], capture_output=True)
s = r.stdout.decode("gbk","replace")
print("NEW in store:", NEW in s, "  OLD still there:", OLD in s)
'''
hp = os.path.join(STAGE, "inst_ca_sha1.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
req = {"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
r=json.loads(b.decode("utf-8"))
print("rc:", r.get("rc"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:300])

import json, os, socket
helper = r'''
import subprocess
r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"], capture_output=True)
pids = [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]
if not pids:
    print("NO_GAME"); raise SystemExit(0)
pid = pids[0]
print("pid:", pid)
r = subprocess.run(["powershell","-NoProfile","-Command",
  "(Get-Process -Id %d).Modules | ForEach-Object { $_.ModuleName }" % pid], capture_output=True)
mods = r.stdout.decode("utf-8","replace").split()
print("total modules:", len(mods))
for m in sorted(mods):
    print("  ", m)
'''
STAGE = r"D:\z7tmp"
hp = os.path.join(STAGE, "mods2.py")
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
print(r.get("stdout"))

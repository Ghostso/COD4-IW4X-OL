import json, os, socket
helper = r'''
import subprocess
r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"], capture_output=True)
pids = [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]
print("game pids:", pids)
if not pids:
    print("NO_GAME"); raise SystemExit(0)
pid = pids[0]
# list modules via powershell (works elevated)
r = subprocess.run(["powershell","-NoProfile","-Command",
  "$p = Get-Process -Id %d; $p.Modules | Where-Object { $_.ModuleName -match 'tcj|tas|TCJ|TAS|Ten|ACE|TerSafe|TP3|VSD' } | ForEach-Object { '{0}|{1}' -f $_.ModuleName, $_.FileName }" % pid],
  capture_output=True)
print(r.stdout.decode("utf-8","replace"))
print("--- err ---")
print(r.stderr.decode("utf-8","replace")[:300])
'''
STAGE = r"D:\z7tmp"; os.makedirs(STAGE, exist_ok=True)
hp = os.path.join(STAGE, "mods.py")
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

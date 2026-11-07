import json, os, socket
helper = r'''
import subprocess
r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process | Where-Object {$_.ProcessName -match 'codo|Abo|IIPS|TP3|TQM|VSD'} | ForEach-Object { '{0}|{1}' -f $_.Id,$_.ProcessName }"],
  capture_output=True)
print(r.stdout.decode("utf-8","replace"))
'''
STAGE=r"D:\z7tmp"
hp=os.path.join(STAGE,"procs.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
st=json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"),encoding="utf-8"))
req={"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s=socket.create_connection(("127.0.0.1",int(st["port"])),timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
print(json.loads(b.decode("utf-8")).get("stdout"))

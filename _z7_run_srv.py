# -*- coding: utf-8 -*-
import os, subprocess, sys, time
LS = os.path.join("CODOLServer","lobby_server")
PY = sys.executable
LOGD = os.path.join(LS,"run_2339")
os.makedirs(LOGD, exist_ok=True)
jobs = [
  ("auth8443", os.path.join(LS,"lobby_probe_server.py"),
   ["--cert-dir",LS,"--bind","127.0.0.1","--port","8443","--log",os.path.join(LOGD,"auth8443.jsonl")]),
  ("lsg8444", os.path.join(LS,"lobby_plain_probe.py"),
   ["--bind","127.0.0.2","--port","8444","--log",os.path.join(LOGD,"lsg8444.jsonl"),
    "--lobby-handshake","--magic","0xDC","--hold-after-83","120"]),
]
for name, script, args in jobs:
    argv = [PY,"-X","utf8","-u",script]+args
    p = subprocess.Popen(argv,
        stdout=open(os.path.join(LOGD,name+".out"),"wb"),
        stderr=open(os.path.join(LOGD,name+".err"),"wb"),
        creationflags=0x08000000)
    print("%-9s pid=%d" % (name,p.pid))
    time.sleep(1.5)
    if p.poll() is not None:
        print("  DIED")
        print(open(os.path.join(LOGD,name+".err"),"rb").read().decode("utf-8","replace")[-500:])
print()
print(open(os.path.join(LOGD,"auth8443.jsonl"),"rb").read().decode("utf-8","replace"))

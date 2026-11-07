# -*- coding: utf-8 -*-
"""Reproduce the healthy round's exact args to confirm the baseline."""
import json, os, socket
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        r"run_codol_001\elevated_ifs1_observer.ps1",
        "-DurationSeconds","120",
        "-Sandbox", r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923",
        "-TenProxyShm", r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_subagents\_tenproxy_shm_fixed.bin",
        "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
        "-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
        "-Post83Trace","1","-Post83Seconds","70",
        "-PokeLobby644","1","-PatchDelay","42","-Patch85Pass","1"]
req={"action":"run","argv":argv,"token":st["token"]}
s=socket.create_connection(("127.0.0.1",int(st["port"])),timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
print(json.loads(b.decode("utf-8")).get("stdout","")[:600])

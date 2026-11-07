# -*- coding: utf-8 -*-
"""Decisive test: do NOT poke lobby globals. Let hosts+dwauth drive the connect."""
import json, os, socket, subprocess, threading, time
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))

seen = []
stop = threading.Event()
def poll():
    while not stop.is_set():
        try:
            r = subprocess.run(["netstat","-ano"], capture_output=True)
            for line in r.stdout.decode("gbk","replace").splitlines():
                if ("3074" in line or "8443" in line or "8444" in line) and "LISTEN" not in line:
                    k = line.strip()
                    if k not in seen:
                        seen.append(k); print("  NET:", k, flush=True)
        except Exception:
            pass
        time.sleep(1.0)

threading.Thread(target=poll, daemon=True).start()

LD = r"CODOLServer\logs\Z7_3074"
os.makedirs(LD, exist_ok=True)
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        r"run_codol_001\elevated_ifs1_observer.ps1",
        "-DurationSeconds","130",
        "-Sandbox", r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929",
        "-TenProxyShm", r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_subagents\_tenproxy_shm_fixed.bin",
        "-PokeE57","0x00E57A5A",
        "-LobbyReadyOnly","1",
        "-Post83Trace","1","-Post83Seconds","90",
        "-HandshakeReadyFile", os.path.abspath(os.path.join(LD,"ready.flag")),
        "-HandshakeEchoFile", os.path.abspath(os.path.join(LD,"echo.txt")),
        "-HandshakeKeyFile", os.path.abspath(os.path.join(LD,"rx.txt")),
        "-HandshakeTxFile", os.path.abspath(os.path.join(LD,"tx.txt")),
        "-HandshakeSessionFile", os.path.abspath(os.path.join(LD,"session.txt")),
        "-PatchDelay","42","-Patch85Pass","1"]
print("NOTE: no -PokeLobbyGlobals, no -PokeLobbyHost/Port", flush=True)
req={"action":"run","argv":argv,"token":st["token"]}
s=socket.create_connection(("127.0.0.1",int(st["port"])),timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
stop.set()
print("\n=== observed connections ===")
for x in seen: print(" ", x)
if not seen: print("  (none)")

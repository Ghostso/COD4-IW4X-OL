# -*- coding: utf-8 -*-
"""Launch, then poll netstat for connections to 3074 / to our servers."""
import json, os, socket, subprocess, threading, time
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))

seen = []
stop = threading.Event()
def poll():
    while not stop.is_set():
        try:
            r = subprocess.run(["netstat","-ano"], capture_output=True)
            txt = r.stdout.decode("gbk","replace")
            for line in txt.splitlines():
                if "3074" in line or "8443" in line or "8444" in line:
                    t = line.split()
                    if t and t[0].startswith("TCP") and "LISTEN" not in line:
                        key = line.strip()
                        if key not in seen:
                            seen.append(key)
                            print("  NET:", key, flush=True)
        except Exception:
            pass
        time.sleep(1.0)

th = threading.Thread(target=poll, daemon=True); th.start()

LD = r"CODOLServer\logs\Z7_3074"
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        r"run_codol_001\elevated_ifs1_observer.ps1",
        "-DurationSeconds","130",
        "-Sandbox", r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929",
        "-TenProxyShm", r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_subagents\_tenproxy_shm_fixed.bin",
        "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","3074",
        "-PokeE57","0x00E57A5A",
        "-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
        "-Post83Trace","1","-Post83Seconds","90",
        "-HandshakeReadyFile", os.path.abspath(os.path.join(LD,"ready.flag")),
        "-HandshakeEchoFile", os.path.abspath(os.path.join(LD,"echo.txt")),
        "-PatchDelay","42","-Patch85Pass","1"]
req={"action":"run","argv":argv,"token":st["token"]}
s=socket.create_connection(("127.0.0.1",int(st["port"])),timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
stop.set()
print("\n=== 观察到的网络连接 ===")
for x in seen: print(" ", x)
print("  (none)" if not seen else "")

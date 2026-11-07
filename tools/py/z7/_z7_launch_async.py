import json, os, socket, subprocess, sys
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
LD = os.path.join(os.getcwd(), "CODOLServer","logs","Z7_3074")
os.makedirs(LD, exist_ok=True)
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
    os.path.join("run_codol_001","elevated_ifs1_observer.ps1"),
    "-DurationSeconds","150",
    "-Sandbox", os.path.join(os.getcwd(),"run_codol_001","sandbox_datafix_20260929"),
    "-TenProxyShm", os.path.join(os.getcwd(),"CODOLServer","_subagents","_tenproxy_shm_fixed.bin"),
    "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
    "-PokeE57","0x00E57A5A","-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
    "-Post83Trace","1","-Post83Seconds","90",
    "-HandshakeReadyFile", os.path.join(LD,"ready.flag"),
    "-HandshakeEchoFile", os.path.join(LD,"echo.txt"),
    "-PatchDelay","42","-Patch85Pass","1"]
req = {"action":"run","argv":argv,"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=900)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
print("launcher done")

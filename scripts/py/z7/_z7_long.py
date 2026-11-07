import json, os, socket
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
LD = os.path.abspath(os.path.join("CODOLServer","logs","Z7_3074"))
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
    os.path.join("run_codol_001","elevated_ifs1_observer.ps1"),
    "-DurationSeconds","190",
    "-Sandbox", os.path.abspath(os.path.join("run_codol_001","sandbox_ifs1_20260923")),
    "-TenProxyShm", os.path.abspath(os.path.join("CODOLServer","_subagents","_tenproxy_shm_fixed.bin")),
    "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
    "-PokeLobbyGlobals","1","-LobbyReadyOnly","1","-Post83Trace","1","-Post83Seconds","120",
    "-HandshakeReadyFile", os.path.join(LD,"ready.flag"),
    "-HandshakeEchoFile", os.path.join(LD,"echo.txt"),
    "-HandshakeKeyFile", os.path.join(LD,"rx.txt"),
    "-HandshakeTxFile", os.path.join(LD,"tx.txt"),
    "-HandshakeSessionFile", os.path.join(LD,"session.txt")]
req = {"action":"run","argv":argv,"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=900)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
print("done")

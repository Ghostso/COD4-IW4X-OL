import json, os, socket, subprocess, sys, time, re

st = json.load(open("CODOLServer/logs/elevated_agent.json", encoding="utf-8"))
LOGD = os.path.abspath("CODOLServer/logs/z7fix")
PJ = os.path.join(LOGD, "probe.jsonl")

# clear log BEFORE probe start (fresh handle)
open(PJ, "w").close()

# restart auth probe with fresh handle
r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'lobby_probe_server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
  capture_output=True)
time.sleep(2)
probe = subprocess.Popen(
    [sys.executable, "-X", "utf8", "-u",
     r"CODOLServer\lobby_server\lobby_probe_server.py",
     "--cert-dir", r"CODOLServer\lobby_server",
     "--bind", "127.0.0.1", "--port", "8443", "--log", PJ],
    stdout=open(os.path.join(LOGD,"auth.out"),"wb"),
    stderr=open(os.path.join(LOGD,"auth.err"),"wb"),
    creationflags=0x08000000)
time.sleep(4)

# clear state, kill game
try: os.remove(r"D:\z7tmp\secrets.txt")
except OSError: pass
subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process | Where-Object { $_.ProcessName -match 'codoMP|AboProbe|TQMCenter|IIPSHostApp' } | Stop-Process -Force -ErrorAction SilentlyContinue"],
  capture_output=True)
time.sleep(26)

# run game THROUGH THE AGENT (elevated)
LD = os.path.abspath("CODOLServer/logs/Z7_3074")
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
    "run_codol_001/elevated_ifs1_observer.ps1",
    "-DurationSeconds","120",
    "-Sandbox", os.path.abspath("run_codol_001/sandbox_ifs1_20260923"),
    "-NoTenProxyShm","1",
    "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
    "-LobbyPort3074","3074",
    "-SecretsFile","D:\\z7tmp\\secrets.txt",
    "-Compat4","1",
    "-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
    "-Post83Trace","1","-Post83Seconds","80",
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
time.sleep(2)

print("=== probe events ===")
for line in open(PJ, encoding="utf-8"):
    mm = re.search(r'"event": "([^"]+)"', line)
    if not mm: continue
    e = mm.group(1); x=""
    m2 = re.search(r'"request_auth_task": "([^"]+)"', line)
    if m2: x += " in=" + m2.group(1)
    m3 = re.search(r'"response_auth_task": ([^,}]+)', line)
    if m3: x += " out=" + m3.group(1)
    print(" ", e, x)

# state machine
import glob
runs = sorted(glob.glob("run_codol_001/runs/IFS1_ELEVATED_*"), key=os.path.getmtime)
if runs:
    d = runs[-1]
    print("\n=== state (%s) ===" % os.path.basename(d))
    csvs = glob.glob(os.path.join(d, "**", "*_state.csv"), recursive=True)
    if csvs:
        rows = open(csvs[0], encoding="utf-8").read().splitlines()
        if len(rows) > 1:
            hdr = rows[0].split(",")
            idx = {n:i for i,n in enumerate(hdr)}
            last=""
            for r2 in rows[1:]:
                c = r2.split(",")
                nm = c[idx["dw_state_name"]]
                if nm != last:
                    last = nm
                    print("  t=%s name=%r code=%s sub=%s" % (
                        c[idx["t"]], nm, c[idx["obj_code"]], c[idx["sub_state"]]))

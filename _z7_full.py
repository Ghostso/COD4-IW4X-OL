import json, os, socket, subprocess, sys, time, re, glob

st = json.load(open("CODOLServer/logs/elevated_agent.json", encoding="utf-8"))
LOGD = os.path.abspath("CODOLServer/logs/z7fix")
PJ = os.path.join(LOGD, "probe.jsonl")

# kill old lsg
subprocess.run(["powershell","-NoProfile","-Command",
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'lsg_server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
  capture_output=True)
time.sleep(2)

# start fresh lsg
lsg = subprocess.Popen(
    [sys.executable, "-X", "utf8", "-u",
     r"CODOLServer\lobby3074\lsg_server.py",
     "--bind", "127.0.0.1", "--port", "3074",
     "--secrets", r"D:\z7tmp\secrets.txt",
     "--log", os.path.abspath(r"CODOLServer\lobby3074\logs\lsg3074.log")],
    stdout=open(os.path.join(LOGD,"lsg2.out"),"wb"),
    stderr=open(os.path.join(LOGD,"lsg2.err"),"wb"),
    creationflags=0x08000000)
time.sleep(3)

# clear files
for f in [r"D:\z7tmp\secrets.txt", r"D:\z7tmp\field648.txt",
          os.path.abspath(r"CODOLServer\logs\Z7_3074\echo.txt")]:
    try: os.remove(f)
    except OSError: pass

# kill game
subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process | Where-Object { $_.ProcessName -match 'codoMP|AboProbe|TQMCenter|IIPSHostApp' } | Stop-Process -Force -ErrorAction SilentlyContinue"],
  capture_output=True)
time.sleep(26)

# run game
LD = os.path.abspath("CODOLServer/logs/Z7_3074")
argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
    "run_codol_001/elevated_ifs1_observer.ps1",
    "-DurationSeconds","90",
    "-Sandbox", os.path.abspath("run_codol_001/sandbox_ifs1_20260923"),
    "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
    "-LobbyPort3074","3074",
    "-SecretsFile","D:\\z7tmp\\secrets.txt",
    "-Compat4","1",
    "-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
    "-Post83Trace","1","-Post83Seconds","60",
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

# report state
runs = sorted(glob.glob("run_codol_001/runs/IFS1_ELEVATED_*"), key=os.path.getmtime)
if runs:
    d = runs[-1]
    print("state:", os.path.basename(d))
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
                    print("  t=%s %r uA50=%s code=%s" % (
                        c[0], nm, c[idx.get("uA50",0)], c[idx.get("obj_code",0)]))

# report lsg log
lsl = os.path.abspath(r"CODOLServer\lobby3074\logs\lsg3074.log")
print("\n=== lsg ===")
try:
    for line in open(lsl, encoding="utf-8"):
        if re.search(r"hmac|task|reply|arm|closed|error|retry|f648|push", line):
            print(" ", line.rstrip()[:200])
except OSError: pass

# check field648
f648 = r"D:\z7tmp\field648.txt"
print("\nfield648:", open(f648).read().strip() if os.path.isfile(f648) else "NOT WRITTEN")

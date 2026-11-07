# -*- coding: utf-8 -*-
"""Try several response auth_task values; record which one clears 735."""
import json, os, re, socket, subprocess, sys, time, glob

st = json.load(open("CODOLServer/logs/elevated_agent.json", encoding="utf-8"))
LOGD = os.path.abspath("CODOLServer/logs/z7fix")
PJ = os.path.join(LOGD, "probe.jsonl")
TPL = os.path.abspath(r"CODOLServer\lobby_server\lobby_response.json")
orig = open(TPL, "rb").read()

def set_task(v):
    p = orig.replace(b"$AUTH_TASK", str(v).encode())
    open(TPL, "wb").write(p)

def one_round(v):
    set_task(v)
    open(PJ, "w").close()
    subprocess.run(["powershell","-NoProfile","-Command",
      "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'lobby_probe_server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
      capture_output=True)
    time.sleep(2)
    subprocess.Popen(
        [sys.executable, "-X", "utf8", "-u",
         r"CODOLServer\lobby_server\lobby_probe_server.py",
         "--cert-dir", r"CODOLServer\lobby_server",
         "--bind", "127.0.0.1", "--port", "8443", "--log", PJ],
        stdout=open(os.path.join(LOGD,"auth.out"),"wb"),
        stderr=open(os.path.join(LOGD,"auth.err"),"wb"),
        creationflags=0x08000000)
    time.sleep(4)
    try: os.remove(r"D:\z7tmp\secrets.txt")
    except OSError: pass
    subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process | Where-Object { $_.ProcessName -match 'codoMP|AboProbe|TQMCenter|IIPSHostApp' } | Stop-Process -Force -ErrorAction SilentlyContinue"],
      capture_output=True)
    time.sleep(26)
    LD = os.path.abspath("CODOLServer/logs/Z7_3074")
    argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        "run_codol_001/elevated_ifs1_observer.ps1",
        "-DurationSeconds","90",
        "-Sandbox", os.path.abspath("run_codol_001/sandbox_ifs1_20260923"),
        "-NoTenProxyShm","1",
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
    got = None
    for line in open(PJ, encoding="utf-8"):
        m = re.search(r'"request_auth_task": "([^"]+)"', line)
        if m: got = m.group(1)
    runs = sorted(glob.glob("run_codol_001/runs/IFS1_ELEVATED_*"), key=os.path.getmtime)
    code = ""
    states = ""
    if runs:
        csvs = glob.glob(os.path.join(runs[-1], "**", "*_state.csv"), recursive=True)
        if csvs:
            rows = open(csvs[0], encoding="utf-8").read().splitlines()
            if len(rows) > 1:
                hdr = rows[0].split(",")
                idx = {n:i for i,n in enumerate(hdr)}
                states = ",".join(dict.fromkeys(
                    r.split(",")[idx["dw_state_name"]] for r in rows[1:] if r.split(",")[idx["dw_state_name"]]))
                codes = set()
                for r in rows[1:]:
                    c = r.split(",")
                    if c[idx["obj_code"]] and c[idx["obj_code"]] != "0":
                        codes.add(c[idx["obj_code"]])
                code = ",".join(codes)
    return got, code, states

for v in (2, 3, 4, 5):
    got, code, states = one_round(v)
    print("reply=%s  client_sent=%s  codes=%s  states=%s" % (v, got, code or "-", states[:120]))
    sys.stdout.flush()

set_task(2)  # restore to the last-tried value

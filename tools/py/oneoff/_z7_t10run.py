import json, os, socket, subprocess, sys, time

LOGD = os.path.abspath("CODOLServer/logs/z7fix")
PJ = os.path.join(LOGD, "probe.jsonl")

# 1. kill old auth probe
r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'lobby_probe_server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
  capture_output=True)
time.sleep(2)

# 2. clear log BEFORE starting the probe (so its handle stays valid)
open(PJ, "w").close()

# 3. start probe
env = dict(os.environ)
probe = subprocess.Popen(
    [sys.executable, "-X", "utf8", "-u",
     r"CODOLServer\lobby_server\lobby_probe_server.py",
     "--cert-dir", r"CODOLServer\lobby_server",
     "--bind", "127.0.0.1", "--port", "8443", "--log", PJ],
    stdout=open(os.path.join(LOGD,"auth.out"),"wb"),
    stderr=open(os.path.join(LOGD,"auth.err"),"wb"),
    creationflags=0x08000000)
print("probe pid:", probe.pid)
time.sleep(4)

# 4. clear state + kill game
try: os.remove(r"D:\z7tmp\secrets.txt")
except OSError: pass
subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process | Where-Object { $_.ProcessName -match 'codoMP|AboProbe|TQMCenter|IIPSHostApp' } | Stop-Process -Force -ErrorAction SilentlyContinue"],
  capture_output=True)
time.sleep(26)

# 5. run the game (objB path)
r = subprocess.run([sys.executable, "-X", "utf8", "_z7_objB.py"],
                   capture_output=True, timeout=300)
print("game run rc:", r.returncode)
time.sleep(2)

# 6. report probe events
print("\n=== probe events ===")
try:
    for line in open(PJ, encoding="utf-8"):
        m = None
        import re
        mm = re.search(r'"event": "([^"]+)"', line)
        if not mm: continue
        e = mm.group(1)
        x = ""
        m2 = re.search(r'"request_auth_task": "([^"]+)"', line)
        if m2: x += " in=" + m2.group(1)
        m3 = re.search(r'"response_auth_task": ([^,}]+)', line)
        if m3: x += " out=" + m3.group(1)
        print(" ", e, x)
except OSError as ex:
    print("read fail:", ex)

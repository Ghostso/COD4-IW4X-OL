import subprocess, sys, os, time
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
PY = sys.executable
OUT  = os.path.join(ROOT, r"CODOLServer\logs\full_image.bin")
LOG  = os.path.join(ROOT, r"CODOLServer\logs\_imagedump.txt")

driver = [PY, "-X", "utf8", os.path.join(ROOT, r"CODOLServer\_mainline\_e57a5c_experiment.py"),
          "--sandbox", os.path.join(ROOT, r"run_codol_001\sandbox_datafix_20260929"),
          "--attempts", "1", "--seconds", "170",
          "--follow-85", "--follow-85-rule", "receive", "--follow-85-cbc",
          "--patch-85-pass", "--plain-port", "8446", "--poke-port", "8443"]
p = subprocess.Popen(driver, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ps(cmd):
    return subprocess.run(["powershell","-NoProfile","-Command", cmd],
                          capture_output=True, text=True, timeout=15).stdout.strip()

def alive(pid):
    return ps("if (Get-Process -Id %d -ErrorAction SilentlyContinue){'1'}else{'0'}" % pid) == '1'

def game_pid():
    r = ps("(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -First 1).Id")
    return int(r) if r.isdigit() else None

pid=None; t0=time.time()
for i in range(120):
    g = game_pid()
    if g and alive(g):
        pid=g; break
    time.sleep(1)
print("game pid", pid, flush=True)
if not pid: print("NO_GAME"); sys.exit(1)

# wait until the game has been up for >=25 s AND still alive (unpacked + lobby)
for i in range(60):
    if not alive(pid): print("died at", time.time()-t0); sys.exit(2)
    if time.time()-t0 > 25: break
    time.sleep(1)
print("dumping at t=%.1f alive=%s" % (time.time()-t0, alive(pid)), flush=True)

exe = os.path.join(ROOT, r"restore_iips_contract_001\observer2\out\AboProbe.exe")
r = subprocess.run([exe, "--imagedump", str(pid), OUT,
                    "--min-va", "0x400000", "--max-va", "0xE659000"],
                   capture_output=True, text=True, timeout=1500)
open(LOG,"w").write((r.stdout or "")+"\n---\n"+(r.stderr or ""))
print("rc", r.returncode, flush=True)
print((r.stdout or "").strip()[:300], flush=True)
if os.path.exists(OUT): print("SIZE", os.path.getsize(OUT), flush=True)

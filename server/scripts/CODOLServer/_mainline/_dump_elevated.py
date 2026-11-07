# Elevated helper: launch the experiment, wait for the game, dump its full image.
import subprocess, sys, os, time, json
PY = sys.executable
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = os.path.join(ROOT, r"CODOLServer\logs\full_image.bin")

driver = [PY, "-X", "utf8", os.path.join(ROOT, r"CODOLServer\_mainline\_e57a5c_experiment.py"),
          "--sandbox", os.path.join(ROOT, r"run_codol_001\sandbox_datafix_20260929"),
          "--attempts", "1", "--seconds", "170",
          "--follow-85", "--follow-85-rule", "receive", "--follow-85-cbc",
          "--reply-85-cbc", "--reply-85-seqs", "1,2,3,4", "--reply-85-arm-first",
          "--patch-85-pass", "--plain-port", "8446", "--poke-port", "8443"]
p = subprocess.Popen(driver, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("driver", p.pid, flush=True)

def game_pid():
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -First 1).Id"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        return int(r) if r.isdigit() else None
    except Exception:
        return None

pid=None
for i in range(90):
    pid = game_pid()
    if pid: break
    time.sleep(1)
print("game pid", pid, flush=True)
if not pid:
    print("NO_GAME", flush=True); sys.exit(1)

time.sleep(12)
exe = os.path.join(ROOT, r"restore_iips_contract_001\observer2\out\AboProbe.exe")
r = subprocess.run([exe, "--imagedump", str(pid), OUT,
                    "--min-va", "0x400000", "--max-va", "0xE659000"],
                   capture_output=True, text=True, timeout=1200)
log = os.path.join(ROOT, r"CODOLServer\logs\_imagedump.txt")
open(log, "w").write((r.stdout or "") + "\n---stderr---\n" + (r.stderr or ""))
print("rc", r.returncode, flush=True)
print((r.stdout or "").strip()[:400], flush=True)
if os.path.exists(OUT):
    print("SIZE", os.path.getsize(OUT), flush=True)

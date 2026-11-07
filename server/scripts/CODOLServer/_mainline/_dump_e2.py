import subprocess, sys, os, time
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
PY = sys.executable
OUT  = os.path.join(ROOT, r"CODOLServer\logs\full_image.bin")

driver = [PY, "-X", "utf8", os.path.join(ROOT, r"CODOLServer\_mainline\_e57a5c_experiment.py"),
          "--sandbox", os.path.join(ROOT, r"run_codol_001\sandbox_datafix_20260929"),
          "--attempts", "1", "--seconds", "170",
          "--follow-85", "--follow-85-rule", "receive", "--follow-85-cbc",
          "--patch-85-pass", "--plain-port", "8446", "--poke-port", "8443"]
p = subprocess.Popen(driver, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("driver", p.pid, flush=True)

def alive(pid):
    r = subprocess.run(["powershell","-NoProfile","-Command",
        "if (Get-Process -Id %d -ErrorAction SilentlyContinue) {'1'} else {'0'}" % pid],
        capture_output=True, text=True, timeout=15).stdout.strip()
    return r == '1'

def game_pid():
    r = subprocess.run(["powershell","-NoProfile","-Command",
        "(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -First 1).Id"],
        capture_output=True, text=True, timeout=15).stdout.strip()
    return int(r) if r.isdigit() else None

# wait for a STABLE game pid (game sometimes starts then dies)
pid=None
for i in range(120):
    g = game_pid()
    if g:
        time.sleep(3)
        if alive(g):
            pid = g; break
    time.sleep(1)
print("stable game pid", pid, flush=True)
if not pid:
    print("NO_GAME", flush=True); sys.exit(1)

# dump immediately in chunks by VA window to reduce per-call load
exe = os.path.join(ROOT, r"restore_iips_contract_001\observer2\out\AboProbe.exe")
for attempt in range(3):
    if not alive(pid):
        print("game died before dump", flush=True); sys.exit(2)
    r = subprocess.run([exe, "--imagedump", str(pid), OUT,
                        "--min-va", "0x400000", "--max-va", "0xE659000"],
                       capture_output=True, text=True, timeout=1200)
    print("attempt", attempt, "rc", r.returncode, (r.stdout or "").strip()[:300], flush=True)
    if os.path.exists(OUT) and os.path.getsize(OUT) > 1000000:
        break
    time.sleep(5)
if os.path.exists(OUT):
    print("SIZE", os.path.getsize(OUT), flush=True)

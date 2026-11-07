import subprocess, sys, os, time, glob
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\full_image.bin"
LOG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\_imagedump.txt"
cmd = [sys.executable, "-X", "utf8",
       r"CODOLServer\_mainline\_e57a5c_experiment.py",
       "--sandbox", r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929",
       "--attempts", "1", "--seconds", "170",
       "--follow-85", "--follow-85-rule", "receive", "--follow-85-cbc",
       "--reply-85-cbc", "--reply-85-seqs", "1,2,3,4", "--reply-85-arm-first",
       "--patch-85-pass",
       "--plain-port", "8446", "--poke-port", "8443"]
p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("driver pid", p.pid, flush=True)

# poll for the game process
import ctypes
def game_pid():
    try:
        out = subprocess.run(["powershell","-NoProfile","-Command",
            "(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -First 1).Id"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        return int(out) if out.isdigit() else None
    except Exception:
        return None

pid=None
for i in range(60):
    pid = game_pid()
    if pid: break
    time.sleep(1)
print("game pid", pid, flush=True)
if not pid:
    print("no game", flush=True); sys.exit(1)

time.sleep(10)   # let it finish unpacking
exe = r"D:\BaiduNetdiskDownload\使命召唤OL\restore_iips_contract_001\observer2\out\AboProbe.exe"
r = subprocess.run([exe, "--imagedump", str(pid), OUT,
                    "--min-va", "0x400000", "--max-va", "0xE659000"],
                   capture_output=True, text=True, timeout=900)
print(r.stdout, r.stderr, flush=True)
open(LOG,"w").write(r.stdout + "\n" + r.stderr)
if os.path.exists(OUT):
    print("dump size", os.path.getsize(OUT), flush=True)

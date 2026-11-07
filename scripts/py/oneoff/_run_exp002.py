import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
CDB = ROOT / "工具" / "windbg_x86" / "cdb.exe"
SCRIPT_NAME = sys.argv[1] if len(sys.argv) > 1 else "exp002.cdb"
LOG_NAME = sys.argv[2] if len(sys.argv) > 2 else SCRIPT_NAME.replace(".cdb", ".log")
EXP_NAME = sys.argv[3] if len(sys.argv) > 3 else "EXPERIMENT_002_DIR"
SCRIPT = ROOT / "工具" / SCRIPT_NAME
LOG = ROOT / "工具" / "logs" / LOG_NAME
EXE = ROOT / "工具" / EXP_NAME / "codoMP_client_shipRetail.exe"

LOG.unlink(missing_ok=True)

p = subprocess.Popen(
    [str(CDB), "-cf", str(SCRIPT), "-logo", str(LOG), str(EXE)],
    cwd=str(ROOT),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT,
)

deadline = time.time() + 40
timed_out = False
while time.time() < deadline:
    if p.poll() is not None:
        break
    time.sleep(0.5)
else:
    timed_out = True

if timed_out:
    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    subprocess.run(["taskkill", "/IM", "codoMP_client_shipRetail.exe", "/F"], capture_output=True)
    subprocess.run(["taskkill", "/IM", "TP3Helper.exe", "/F"], capture_output=True)
    subprocess.run(["taskkill", "/IM", "TQMCenter.exe", "/F"], capture_output=True)

print("CDB_EXIT", p.poll() if not timed_out else "KILLED")
print("TIMED_OUT", timed_out)
if LOG.exists():
    raw = LOG.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    print("===== LOG TAIL =====")
    print("\n".join(lines[-260:]))

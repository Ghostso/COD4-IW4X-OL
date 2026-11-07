"""Experiment A: fake-TQoS redirect + desktop shot loop, run elevated."""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GAME = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923", "codoMP_client_shipRetail.exe")
CWD  = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")

outdir = sys.argv[1]
variant = sys.argv[2] if len(sys.argv) > 2 else "3"
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 110.0

os.makedirs(outdir, exist_ok=True)
redir_out = os.path.join(outdir, "harness")
shots = os.path.join(outdir, "shots")
os.makedirs(shots, exist_ok=True)

py = sys.executable
print("=== launching suspend_host_redirect variant=%s ===" % variant, flush=True)
h = subprocess.Popen([py, "-X", "utf8", "-u",
                      os.path.join(HERE, "suspend_host_redirect.py"),
                      "--exe", GAME, "--cwd", CWD, "--out", redir_out,
                      "--seconds", str(seconds),
                      "--reply-variant", variant],
                     stdout=open(os.path.join(outdir, "harness.stdout.txt"), "w"),
                     stderr=subprocess.STDOUT)
time.sleep(8)
print("=== launching shot loop ===", flush=True)
s = subprocess.Popen([py, "-X", "utf8", "-u", os.path.join(HERE, "_A_shotloop.py"),
                      shots, str(seconds - 6), "3.0"],
                     stdout=open(os.path.join(outdir, "shots.stdout.txt"), "w"),
                     stderr=subprocess.STDOUT)
rc_h = h.wait()
print("harness exit", rc_h, flush=True)
try:
    s.wait(timeout=30)
except Exception:
    s.terminate()
print("done", flush=True)

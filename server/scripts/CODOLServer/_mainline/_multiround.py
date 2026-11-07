"""Multi-attempt experiment runner: keeps only rounds that actually
reached the lobby (life >= 80 s), so a 1/3 startup flake does not
contaminate the comparison."""
import subprocess, sys, os, re, time, json, glob
import threading
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
PY = sys.executable
AGENT = 18428
KEEP = {"formal-zone-lsg"}  # reserved; filter by commandline below
SELF = os.getpid()
SHM_SCRIPT = os.path.join(ROOT, r"CODOLServer\_mainline\_z7_publish_shm.py")
SHM_IMAGE = os.path.join(ROOT, r"CODOLServer\_subagents\_tenproxy_shm.bin")
SHM_PROC = [None]

def _publish_shm_when_ready():
    """Wait for codoMP_client_shipRetail to appear, then publish SHM."""
    for _ in range(240):
        time.sleep(0.5)
        try:
            out = subprocess.run(
                ["powershell","-NoProfile","-Command",
                 "(Get-Process codoMP_client_shipRetail -EA SilentlyContinue).Id"],
                capture_output=True, text=True, timeout=10)
            pid = out.stdout.strip()
            if pid and pid.isdigit():
                p = subprocess.Popen(
                    [PY, "-X", "utf8", SHM_SCRIPT, pid, SHM_IMAGE],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                SHM_PROC[0] = p
                print("  [shm] published TCLS_SHAREDMEMEMORY%s" % pid,
                      flush=True)
                return
        except Exception:
            pass
    print("  [shm] game process not found", flush=True)

def _stop_shm():
    if SHM_PROC[0] is not None:
        SHM_PROC[0].terminate()
        SHM_PROC[0] = None

def clean():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object {{ $_.ProcessId -ne {ag} -and $_.ProcessId -ne {me} "
          "-and $_.CommandLine -notmatch 'fake_auth_tls|lsg_server' }} | "
          "ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}; "
          "Get-Process -Name codoMP_client_shipRetail,AboProbe,IIPSHostApp -ErrorAction SilentlyContinue | "
          "Stop-Process -Force -ErrorAction SilentlyContinue").format(ag=AGENT, me=SELF)
    subprocess.run(["powershell","-NoProfile","-Command",ps],
                   capture_output=True, text=True, timeout=60)

def latest_run_dir():
    ds = glob.glob(os.path.join(ROOT, r"run_codol_001\runs\IFS1_*"))
    return max(ds, key=os.path.getmtime) if ds else None

def lifetime(run_dir):
    f = os.path.join(run_dir, "aboprobe.stdout") if run_dir else None
    if not f or not os.path.exists(f): return None
    try:
        b = open(f,"rb").read()
        x = b.decode("gbk", errors="replace")
        m = re.search(r"lifetime=([\d.]+)", x)
        return float(m.group(1)) if m else None
    except Exception:
        return None

def one_round(extra, seconds=110):
    clean(); time.sleep(14)
    _stop_shm()
    threading.Thread(target=_publish_shm_when_ready, daemon=True).start()
    before = set(glob.glob(os.path.join(ROOT, r"run_codol_001\runs\IFS1_*")))
    cmd=[PY,"-X","utf8",os.path.join(ROOT,r"CODOLServer\_mainline\_e57a5c_experiment.py"),
         "--sandbox",os.path.join(ROOT,r"run_codol_001\sandbox_datafix_20260929"),
         "--attempts","1","--seconds",str(seconds),
         "--plain-port","8446","--poke-port","3074"] + extra
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=500,
                       encoding="utf-8", errors="replace")
    after = set(glob.glob(os.path.join(ROOT, r"run_codol_001\runs\IFS1_*")))
    new = sorted(after - before, key=os.path.getmtime)
    d = new[-1] if new else latest_run_dir()
    life = lifetime(d)
    out = r.stdout or ""
    st = re.search(r"st\s+(\d+)\s+->\s+(\d+)", out)
    ok = life is not None and life >= 80.0
    return {"dir": os.path.basename(d) if d else None, "life": life,
            "ok": ok, "st": st.group(0).strip() if st else None, "rc": r.returncode}

def run_group(tag, extra, need=2, maxtries=5):
    print("=== %s ===" % tag, flush=True)
    good = []
    for i in range(1, maxtries+1):
        res = one_round(extra)
        print("  %s#%d life=%s ok=%s %s" % (tag, i, res["life"], res["ok"], res["st"] or "-"), flush=True)
        if res["ok"]:
            good.append(res)
            if len(good) >= need: break
    print("  %s: valid rounds = %d" % (tag, len(good)), flush=True)
    return good

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--need", type=int, default=2)
    # everything after --tag/--need is passed through to the driver
    a, rest = ap.parse_known_args()
    g = run_group(a.tag, rest, need=a.need)
    print(json.dumps(g, ensure_ascii=False))

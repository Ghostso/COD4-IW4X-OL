import subprocess, sys, os, time
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
PY = sys.executable
OUT  = os.path.join(ROOT, r"CODOLServer\logs\full_image.bin")
LOG  = os.path.join(ROOT, r"CODOLServer\logs\_imagedump.txt")

# Minimal driver invocation: no handshake, just launch + observe for 170 s.
driver = [PY, "-X", "utf8", os.path.join(ROOT, r"CODOLServer\_mainline\_e57a5c_experiment.py"),
          "--sandbox", os.path.join(ROOT, r"run_codol_001\sandbox_datafix_20260929"),
          "--attempts", "1", "--seconds", "170",
          "--plain-port", "8446", "--poke-port", "8443"]
p = subprocess.Popen(driver, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ps(cmd):
    return subprocess.run(["powershell","-NoProfile","-Command",cmd],
                          capture_output=True,text=True,timeout=20).stdout.strip()
def alive(pid): return ps("if (Get-Process -Id %d -ErrorAction SilentlyContinue){'1'}else{'0'}"%pid)=='1'
def game_pid():
    r=ps("(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -First 1).Id")
    return int(r) if r.isdigit() else None

pid=None; t0=time.time()
for i in range(120):
    g=game_pid()
    if g and alive(g): pid=g; break
    time.sleep(0.5)
print("game pid",pid,flush=True)
if not pid: print("NO_GAME"); sys.exit(1)

exe=os.path.join(ROOT, r"restore_iips_contract_001\observer2\out\AboProbe.exe")
best=0; bestt=0
for n in range(12):
    if not alive(pid):
        print("died at t=%.1f"%(time.time()-t0),flush=True); break
    t=time.time()-t0
    tmp=OUT+".t%d"%n
    r=subprocess.run([exe,"--imagedump",str(pid),tmp,
                      "--min-va","0x400000","--max-va","0x0E659000"],
                     capture_output=True,text=True,timeout=600)
    first=(r.stdout or "").strip().splitlines()
    msg=first[0] if first else "?"
    sz=os.path.getsize(tmp) if os.path.exists(tmp) else 0
    print("t=%.1f %s size=%d" % (t, msg, sz), flush=True)
    if sz>best:
        best=sz; bestt=t
        os.replace(tmp,OUT)
        open(LOG,"w").write(r.stdout or "")
    else:
        if os.path.exists(tmp): os.remove(tmp)
    time.sleep(3)
print("BEST size=%d at t=%.1f"%(best,bestt),flush=True)

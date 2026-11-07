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
    return subprocess.run(["powershell","-NoProfile","-Command",cmd],
                          capture_output=True,text=True,timeout=20).stdout.strip()
def alive(pid): return ps("if (Get-Process -Id %d -ErrorAction SilentlyContinue){'1'}else{'0'}"%pid)=='1'
def game_pid():
    r=ps("(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Select-Object -First 1).Id")
    return int(r) if r.isdigit() else None

pid=None
for i in range(120):
    g=game_pid()
    if g and alive(g): pid=g; break
    time.sleep(1)
print("game pid",pid,flush=True)
if not pid: print("NO_GAME"); sys.exit(1)

# dump at several checkpoints; keep the biggest result
exe=os.path.join(ROOT, r"restore_iips_contract_001\observer2\out\AboProbe.exe")
best=0
for wait in (10,20,30,45,60):
    while True:
        if not alive(pid): print("died"); sys.exit(2)
        time.sleep(1)
        if wait<=0: break
        wait-=1
    tmp=OUT+".w%d"%wait
    r=subprocess.run([exe,"--imagedump",str(pid),tmp,
                      "--min-va","0x400000","--max-va","0x0E659000"],
                     capture_output=True,text=True,timeout=1500)
    line=(r.stdout or "").strip().splitlines()
    print("wait",wait,"rc",r.returncode,line[0] if line else "",flush=True)
    if os.path.exists(tmp):
        sz=os.path.getsize(tmp)
        if sz>best:
            best=sz
            os.replace(tmp,OUT)
            open(LOG,"w").write(r.stdout or "")
            print("  new best",sz,flush=True)
        else:
            os.remove(tmp)
print("BEST",best,flush=True)

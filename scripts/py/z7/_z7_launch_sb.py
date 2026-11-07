# -*- coding: utf-8 -*-
import os, subprocess, sys, time
SB = os.path.join(os.getcwd(), "run_codol_001","sandbox_ifs1_20260923")
EXE = os.path.join(SB, "codoMP_client_shipRetail.exe")
print("SB  :", SB)
print("EXE :", EXE, os.path.isfile(EXE))
print()
print("=== iips.ini visible from cwd? ===")
print("  ", os.path.isfile(os.path.join(SB,"iips.ini")))
for name in ["iips.ini","dwauth.ini","cacert.pem"]:
    p=os.path.join(SB,name)
    print("  %-14s %s" % (name, os.path.getsize(p) if os.path.isfile(p) else "MISSING"))
env = dict(os.environ)
env["PATH"] = SB + os.pathsep + env.get("PATH","")
p = subprocess.Popen([EXE], cwd=SB, env=env, creationflags=0x00000008)
print("\nlaunched pid:", p.pid)
t0=time.time()
def gamepids():
    r=subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process | Where-Object {$_.ProcessName -match 'codo|ACE|TP3|IIPS'} | Select-Object -ExpandProperty Id"],
      capture_output=True,text=True)
    return [x for x in r.stdout.split() if x.strip()]
for i in range(30):
    time.sleep(1.0)
    gp = gamepids()
    print("t=%4.1f pids=%s" % (time.time()-t0, gp))
    if not gp and i>3:
        print("  -> all exited")
        break

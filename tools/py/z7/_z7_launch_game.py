# -*- coding: utf-8 -*-
import os, subprocess, sys, time, json
GAME = os.path.join(os.getcwd(), "COD OL")
EXE  = os.path.join(GAME, "codoMP_client_shipRetail.exe")
print("EXE exists:", os.path.isfile(EXE))
print("GAME dir  :", GAME)

# baseline process list
def procs():
    r = subprocess.run(["powershell","-NoProfile","-Command",
        "Get-Process | Where-Object {$_.ProcessName -match 'codo|ACE|TP3|Tenio'} | Select-Object -ExpandProperty Id"],
        capture_output=True, text=True)
    return [x for x in r.stdout.split() if x.strip()]
print("baseline game-ish pids:", procs())

env = dict(os.environ)
env["PATH"] = GAME + os.pathsep + env.get("PATH","")
p = subprocess.Popen([EXE, "-q"], cwd=GAME, env=env,
                     creationflags=0x00000008)  # DETACHED_PROCESS
print("launched pid:", p.pid)
t0 = time.time()
for i in range(40):
    time.sleep(0.5)
    now = procs()
    print("t=%4.1f  live game-ish pids: %s" % (time.time()-t0, now))
    if now:
        break

import subprocess, sys, os, time
# Start a normal experiment in the background so the game process stays alive,
# then dump its full image while it runs.
cmd = [sys.executable, "-X", "utf8",
       r"CODOLServer\_mainline\_e57a5c_experiment.py",
       "--sandbox", r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929",
       "--attempts", "1", "--seconds", "170",
       "--follow-85", "--follow-85-rule", "receive", "--follow-85-cbc",
       "--reply-85-cbc", "--reply-85-seqs", "1,2,3,4", "--reply-85-arm-first",
       "--patch-85-pass",
       "--plain-port", "8446", "--poke-port", "8443"]
p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("launched pid", p.pid)
open(r"CODOLServer\logs\_launcher_pid.txt","w").write(str(p.pid))

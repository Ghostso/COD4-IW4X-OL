import os, sys, time
root = sys.argv[1]
par = os.path.join(root, "incoming", "i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z.parts")
last = 0; stable = 0
while True:
    if os.path.isdir(par):
        files = [f for f in os.listdir(par) if f.endswith(".bin")]
        tot = sum(os.path.getsize(os.path.join(par, f)) for f in files)
    else:
        tot = 0
    proc = os.popen('tasklist /FI "PID eq 17824" /NH').read()
    alive = "python" in proc.lower()
    print(f"{time.strftime('%H:%M:%S')} parts_bytes={tot} alive={alive}", flush=True)
    if not alive and tot >= 45050859 - 524288:
        print("process ended", flush=True); break
    time.sleep(30)

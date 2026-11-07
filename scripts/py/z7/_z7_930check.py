"""Did any run actually reach the lobby (POKE_LOBBY_COMPLETE), or only
'life >= 60 s'?  The distinction matters: the [100] popup is a lobby-stage
error, so a round can live 100 s and still show it.
"""
import glob
import os
import re

RUNS = r"run_codol_001\runs"

rows = []
for d in sorted(glob.glob(os.path.join(RUNS, "IFS1_*")),
                key=os.path.getmtime):
    nm = os.path.basename(d)
    m = re.search(r"_(\d{8})_", nm)
    if not m:
        continue
    f = os.path.join(d, "aboprobe.stdout")
    if not os.path.exists(f):
        continue
    x = open(f, "rb").read().decode("gbk", "replace")
    lm = re.search(r"lifetime=([\d.]+)", x)
    life = float(lm.group(1)) if lm else 0.0
    rows.append((m.group(1), nm, life,
                 "POKE_LOBBY_COMPLETE" in x,
                 "POKE_LOBBY_GLOBALS" in x,
                 "无法连接大厅服务" in x,
                 "与大厅服务失去连接" in x))

print("=== by day: did the LOBBY actually connect? ===")
for day in sorted({r[0] for r in rows}):
    sub = [r for r in rows if r[0] == day]
    n = len(sub)
    conn = sum(1 for r in sub if r[3])
    globals_ = sum(1 for r in sub if r[4])
    pop100 = sum(1 for r in sub if r[5])
    lost = sum(1 for r in sub if r[6])
    mark = ""
    if conn == 0 and globals_ > 0:
        mark = "   <== globals fired but LOBBY_COMPLETE never did"
    print("  %s runs=%-4d LOBBY_COMPLETE=%-4d GLOBALS=%-4d [100]=%-3d lost=%-4d%s"
          % (day, n, conn, globals_, pop100, lost, mark))

print()
print("=== last 5 runs that reached LOBBY_COMPLETE ===")
hit = [r for r in rows if r[3]]
for r in hit[-5:]:
    print("   %-40s life=%-7s [100]=%s" % (r[1][:40], r[2], r[5]))
if not hit:
    print("   (none)")

from pathlib import Path
import time, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
paths=[Path(r"WeGame\log\wegame.20260913-184927-590.log"), Path(r"WeGame\log\wegame.20260913-184947-420.log"), Path(r"WeGame\log\alog\20260913_184939.log"), Path(r"WeGame\log\tcls\log\TCLSHost_2026-9-13-1789296589.log")]
terms=["StartFor","launcher","tgp_daemon","wegame exit","IdleState","addpath","pid","cmd_","login","tcls","game_id","automation","exit"]
for p in paths:
    if not p.exists(): continue
    print("\n"+"="*110, p)
    txt=p.read_text("utf-8",errors="ignore")
    lines=txt.splitlines()
    idx=[]
    for i,l in enumerate(lines):
        if any(t.lower() in l.lower() for t in terms): idx.append(i)
    keep=set()
    for i in idx:
        for j in range(max(0,i-3), min(len(lines),i+4)): keep.add(j)
    for i in sorted(keep): print(f"{i+1}: {lines[i]}")

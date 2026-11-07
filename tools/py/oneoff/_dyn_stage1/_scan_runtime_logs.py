from pathlib import Path
import time, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
roots=[Path(r"WeGame\log"), Path(r"COD OL\WeGameLauncher"), Path(r"COD OL\TCLS"), Path(r"COD OL\Logs"), Path(r"COD OL\TimeLog")]
terms=["StartFor","launcher exit","wegame exit","tgp_daemon","WeGameLauncerApp","launch tcls","TCLS","cmd_launcher","game_id","AddPath","session","context","token","ticket","auth","TCLS_SHARED","error","fail","mutex","pipe","Shared"]
files=[]
for root in roots:
    if not root.exists(): continue
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".log",".txt",".ini",".json",".info"):
            files.append(p)
files.sort(key=lambda p:p.stat().st_mtime, reverse=True)
print("FILES",len(files))
for p in files:
    try: txt=p.read_text("utf-8",errors="ignore")
    except: txt=p.read_bytes().decode("latin1","ignore")
    lines=txt.splitlines()
    hits=[(i+1,l) for i,l in enumerate(lines) if any(t.lower() in l.lower() for t in terms)]
    if hits:
        print("\n"+"="*100)
        print(p, "mtime",time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(p.stat().st_mtime)), "hits",len(hits))
        for i,l in hits[-200:]: print(f"{i}: {l}")

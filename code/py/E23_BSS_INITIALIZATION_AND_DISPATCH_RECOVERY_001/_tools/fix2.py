import hashlib
from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001")
reps=sorted(base.glob("E23_*.md"), key=lambda p:p.name)
lines=[]
for p in reps:
    lines.append("%s  %s"%(hashlib.sha256(p.read_bytes()).hexdigest(), p.name))
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n", encoding="ascii")
# verify
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
reps={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob("E23_*.md")}
print("entries",len(man),"files",len(reps))
print("missing",[n for n in man if n not in reps])
print("extra",[n for n in reps if n not in man])
print("mismatch",[n for n in man if man[n]!=reps[n]])
print("ALL_OK", len(man)==9 and set(man)==set(reps) and all(man[n]==reps[n] for n in man))
print()
print((base/"SHA256SUMS.txt").read_text(encoding="ascii"))

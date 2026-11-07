import hashlib
from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001")
reps=sorted(base.glob("E25_*.md"), key=lambda p:p.name)
print("report count:",len(reps))
lines=[]
for p in reps:
    lines.append("%s  %s"%(hashlib.sha256(p.read_bytes()).hexdigest(),p.name))
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob("E25_*.md")}
print("entries",len(man))
print("missing:",[n for n in man if n not in cur])
print("extra:",[n for n in cur if n not in man])
print("mismatch:",[n for n in man if man[n]!=cur[n]])
print("ALL_OK:", len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))
print()
print((base/"SHA256SUMS.txt").read_text(encoding="ascii"))

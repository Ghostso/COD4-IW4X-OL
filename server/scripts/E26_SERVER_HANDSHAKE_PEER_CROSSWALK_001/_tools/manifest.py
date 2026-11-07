import hashlib
from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001")
reps=sorted(base.glob("E26_*.md"), key=lambda p:p.name)
print("report count:",len(reps))
lines=["%s  %s"%(hashlib.sha256(p.read_bytes()).hexdigest(),p.name) for p in reps]
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob("E26_*.md")}
print("entries",len(man))
print("missing:",[n for n in man if n not in cur])
print("extra:",[n for n in cur if n not in man])
print("mismatch:",[n for n in man if man[n]!=cur[n]])
print("ALL_OK:", len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))
print()
print((base/"SHA256SUMS.txt").read_text(encoding="ascii"))

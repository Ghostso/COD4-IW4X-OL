from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001")
for p in base.glob("E25_*.md"):
    t=p.read_text(encoding="utf-8")
    n=t.replace("0x6ABAF C","0x6ABAFC")
    if n!=t: p.write_text(n,encoding="utf-8"); print("fixed",p.name)
# final scan
bad=0
for p in sorted(base.glob("E25_*.md")):
    t=p.read_text(encoding="utf-8")
    for pat in ("TODO","FIXME","0x6ABAF C","0x4DAB40  ","DSS"):
        if pat in t: print("flag",p.name,repr(pat)); bad+=1
print("flags:",bad)
# regenerate manifest
import hashlib
reps=sorted(base.glob("E25_*.md"), key=lambda x:x.name)
lines=["%s  %s"%(hashlib.sha256(x.read_bytes()).hexdigest(),x.name) for x in reps]
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in base.glob("E25_*.md")}
print("manifest OK:", len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))

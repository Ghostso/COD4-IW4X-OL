import hashlib
from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")
reps=sorted(base.glob("E24_*.md"), key=lambda p:p.name)
print("report count:",len(reps))
lines=[]
for p in reps:
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    lines.append("%s  %s"%(h,p.name))
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n", encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob("E24_*.md")}
print("manifest entries:",len(man))
print("missing:",[n for n in man if n not in cur])
print("extra:",[n for n in cur if n not in man])
print("mismatch:",[n for n in man if n in cur and man[n]!=cur[n]])
print("ALL_OK:", len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))
print()
print((base/"SHA256SUMS.txt").read_text(encoding="ascii"))
print("--- frozen samples ---")
frozen=[(r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe","353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1"),
        (r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin","24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4"),
        (r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe","80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1")]
for f,exp in frozen:
    g=hashlib.sha256(Path(f).read_bytes()).hexdigest()
    print("  %s  %s" % ("MATCH" if g==exp else "MISMATCH", Path(f).name))

from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")
p=base/"E24_HANDSHAKE_OPCODE_DIRECTION_MATRIX.md"; t=p.read_text(encoding="utf-8")
t=t.replace("| 0x81 | `0x6AB655`（构造应答）","| 0x81 | `0x6AB66D`（构造应答）")
p.write_text(t,encoding="utf-8")
# regenerate manifest
import hashlib
reps=sorted(base.glob("E24_*.md"), key=lambda x:x.name)
lines=["%s  %s"%(hashlib.sha256(x.read_bytes()).hexdigest(),x.name) for x in reps]
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in base.glob("E24_*.md")}
print("entries",len(man),"missing",[n for n in man if n not in cur],"extra",[n for n in cur if n not in man],"mismatch",[n for n in man if man[n]!=cur[n]])
print("ALL_OK",len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))

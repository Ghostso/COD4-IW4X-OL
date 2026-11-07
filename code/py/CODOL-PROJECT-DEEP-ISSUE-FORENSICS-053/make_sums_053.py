import hashlib,os
HERE=os.getcwd()
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<20), b""): h.update(b)
    return h.hexdigest()
lines=[]
for dp,dns,fns in os.walk(HERE):
    dns[:] = [d for d in dns if d not in ("__pycache__",)]
    for fn in sorted(fns):
        if fn=="SHA256SUMS.txt": continue
        p=os.path.join(dp,fn)
        rel=os.path.relpath(p,HERE).replace("\\","/")
        lines.append("%s  %s"%(sha(p),rel))
lines.sort(key=lambda x:x.split("  ",1)[1])
open(os.path.join(HERE,"SHA256SUMS.txt"),"w",encoding="utf-8",newline="\n").write("\n".join(lines)+"\n")
print("wrote",len(lines),"entries")

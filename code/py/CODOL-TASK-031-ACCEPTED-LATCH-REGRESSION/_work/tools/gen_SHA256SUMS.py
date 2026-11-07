import os, hashlib, time
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION"
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()
targets=[]
for fn in sorted(os.listdir(OUT)):
    fp=os.path.join(OUT,fn)
    if os.path.isfile(fp) and fn!="SHA256SUMS.txt": targets.append(fp)
for sub in ("evidence","integrity"):
    d=os.path.join(OUT,sub)
    for dp,_,fs in os.walk(d):
        for fn in sorted(fs): targets.append(os.path.join(dp,fn))
lines=["# CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION - SHA-256 integrity list",
       "# generated: "+time.strftime("%Y-%m-%dT%H:%M:%S%z"),
       "# revision: 2 (evidence-validity correction; dynamic results downgraded to INVALID_PRECONDITION)",
       "# note: paths are relative to this manifest's directory",""]
for fp in targets:
    lines.append("%s  %s" % (sha(fp), os.path.relpath(fp,OUT).replace(os.sep,"/")))
open(os.path.join(OUT,"SHA256SUMS.txt"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print(len(lines)-5,"entries")

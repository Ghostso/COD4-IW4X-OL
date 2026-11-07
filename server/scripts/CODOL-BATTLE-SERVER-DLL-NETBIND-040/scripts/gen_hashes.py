# -*- coding: utf-8 -*-
import io, os, hashlib
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
def sha(p):
    h=hashlib.sha256(); h.update(open(p,"rb").read()); return h.hexdigest()
# deliverable set (top-level)
top=[]
for f in sorted(os.listdir(ROOT)):
    p=os.path.join(ROOT,f)
    if os.path.isfile(p): top.append(f)
# include scripts + evidence
extra=[]
for sub in ("scripts","evidence"):
    d=os.path.join(ROOT,sub)
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            p=os.path.join(d,f)
            if os.path.isfile(p): extra.append(sub+"/"+f)
# exclude manifest files themselves from listing (they are outputs) but include in sums at end
exclude={"FILE_HASH_MANIFEST.tsv","SHA256SUMS.txt"}
rows=[]
for f in top+extra:
    if f.split("/")[-1] in exclude: continue
    rows.append((f, sha(os.path.join(ROOT,f.replace("/",os.sep)))))
# FILE_HASH_MANIFEST.tsv
lines=["REL_PATH\tSHA256\tBYTES\n"]
for f,h in rows:
    lines.append("%s\t%s\t%d\n"%(f,h,os.path.getsize(os.path.join(ROOT,f.replace("/",os.sep)))))
io.open(os.path.join(ROOT,"FILE_HASH_MANIFEST.tsv"),"w",encoding="utf-8",newline="").write("".join(lines))
# SHA256SUMS.txt (sha256sum compatible) - list all incl. manifest
final=[]
for f,h in rows:
    final.append((h,f))
# add manifest itself
fh=sha(os.path.join(ROOT,"FILE_HASH_MANIFEST.tsv"))
final.append((fh,"FILE_HASH_MANIFEST.tsv"))
s="".join("%s  %s\n"%(h,f) for h,f in final)
io.open(os.path.join(ROOT,"SHA256SUMS.txt"),"w",encoding="utf-8",newline="").write(s)
print("files hashed:",len(rows))
w=io.open(os.path.join(ROOT,"FILE_HASH_MANIFEST.tsv"),encoding="utf-8"); print("manifest lines:",sum(1 for _ in w))

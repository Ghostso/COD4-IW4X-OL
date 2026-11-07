# -*- coding: utf-8 -*-
import os, io, hashlib
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043"
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()
files=[]
for base,dirs,names in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d!='__pycache__']
    for n in names:
        p=os.path.join(base,n)
        rel=os.path.relpath(p,ROOT).replace('\\','/')
        if rel in ('SHA256SUMS.txt','FILE_HASH_MANIFEST.tsv'): continue
        files.append((rel,p))
files.sort()
man=["REL_PATH\tSHA256\tBYTES"]
for rel,p in files: man.append("%s\t%s\t%d"%(rel,sha(p),os.path.getsize(p)))
io.open(os.path.join(ROOT,'FILE_HASH_MANIFEST.tsv'),'w',encoding='utf-8',newline='').write("\n".join(man)+"\n")
sums=sorted("%s  *%s"%(sha(p),rel) for rel,p in files)
sums.append("%s  *FILE_HASH_MANIFEST.tsv"%sha(os.path.join(ROOT,'FILE_HASH_MANIFEST.tsv')))
io.open(os.path.join(ROOT,'SHA256SUMS.txt'),'w',encoding='utf-8',newline='').write("\n".join(sums)+"\n")
print("files:",len(files))
# independent verify
ok=fail=miss=0
for line in io.open(os.path.join(ROOT,'SHA256SUMS.txt'),encoding='utf-8'):
    line=line.rstrip('\n')
    if not line.strip(): continue
    h,rest=line.split('  *',1)
    p=os.path.join(ROOT,rest.replace('/',os.sep))
    if not os.path.isfile(p): miss+=1; continue
    if sha(p)==h: ok+=1
    else: fail+=1; print("MISMATCH",rest)
print("verify ok=%d fail=%d missing=%d"%(ok,fail,miss))

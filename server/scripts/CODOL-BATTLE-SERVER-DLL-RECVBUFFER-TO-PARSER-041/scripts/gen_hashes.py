# -*- coding: utf-8 -*-
import sys, os, io, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

# collect all files except SHA256SUMS.txt and FILE_HASH_MANIFEST.tsv themselves
files=[]
for base,dirs,names in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ('__pycache__',)]
    for n in names:
        p=os.path.join(base,n)
        rel=os.path.relpath(p,ROOT).replace('\\','/')
        if rel in ('SHA256SUMS.txt','FILE_HASH_MANIFEST.tsv'): continue
        files.append((rel,p))
files.sort()

man=["REL_PATH\tSHA256\tBYTES"]
for rel,p in files:
    man.append("%s\t%s\t%d"%(rel,sha(p),os.path.getsize(p)))
io.open(os.path.join(ROOT,'FILE_HASH_MANIFEST.tsv'),'w',encoding='utf-8',newline='').write("\n".join(man)+"\n")

# SHA256SUMS.txt: includes manifest too
sums=[]
for rel,p in files:
    sums.append("%s  *%s"%(sha(p),rel))
sums.append("%s  *%s"%(sha(os.path.join(ROOT,'FILE_HASH_MANIFEST.tsv')),'FILE_HASH_MANIFEST.tsv'))
sums.sort()
io.open(os.path.join(ROOT,'SHA256SUMS.txt'),'w',encoding='utf-8',newline='').write("\n".join(sums)+"\n")
print("files:",len(files))
print("manifest + SHA256SUMS written")

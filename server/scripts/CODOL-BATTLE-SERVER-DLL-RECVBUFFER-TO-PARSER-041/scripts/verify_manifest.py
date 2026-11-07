# -*- coding: utf-8 -*-
import os,hashlib,io
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041"
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
# parse SHA256SUMS.txt and verify
ok=fail=0; missing=[]
for line in io.open(os.path.join(ROOT,'SHA256SUMS.txt'),encoding='utf-8'):
    line=line.rstrip('\n')
    if not line.strip(): continue
    h,rest=line.split('  *',1)
    p=os.path.join(ROOT,rest.replace('/',os.sep))
    if not os.path.isfile(p): missing.append(rest); continue
    if sha(p)==h: ok+=1
    else: fail+=1; print("MISMATCH",rest)
print("SHA256SUMS verify: ok=%d fail=%d missing=%d"%(ok,fail,len(missing)))
for m in missing: print("  missing",m)

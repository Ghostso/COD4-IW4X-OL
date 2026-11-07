import os,re,glob
root=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
files=glob.glob(os.path.join(root,'**','*.tdr'),recursive=True)
kw=re.compile(r'(host|port|addr|url|domain|server|svr|lobby|auth|ticket|queue|member|login|zone|world|qos|room|match)',re.I)
for p in files:
    d=open(p,'rb').read()
    strings=[m.group().decode('ascii','replace') for m in re.finditer(rb'[\x20-\x7e]{4,}',d)]
    hits=[s for s in strings if kw.search(s)]
    if hits:
        print('\n##### %s (%d bytes, %d fields)'%(os.path.relpath(p,root),len(d),len(strings)))
        for s in hits[:80]: print('  ',s)

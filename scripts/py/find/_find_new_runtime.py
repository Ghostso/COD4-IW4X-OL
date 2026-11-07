import os, time, datetime, json
roots=[r'D:\BaiduNetdiskDownload\使命召唤OL',os.path.expandvars(r'%USERPROFILE%\Downloads'),os.path.expandvars(r'%USERPROFILE%\Desktop'),os.path.expandvars(r'%USERPROFILE%\Documents'),os.environ.get('TEMP'),os.path.expandvars(r'%LOCALAPPDATA%\CrashDumps')]
cut=time.time()-3*86400
rows=[]
for root in roots:
    if not root or not os.path.isdir(root): continue
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d.lower() not in ('.git','node_modules','__pycache__')]
        for n in fn:
            low=n.lower()
            if low.endswith('.tvm0'): continue
            p=os.path.join(dp,n)
            try: st=os.stat(p)
            except OSError: continue
            if st.st_size < 1_000_000: continue
            if st.st_mtime < cut and not any(k in low for k in ('dump','memory','minidump','crash','codomp','shipretail')):
                continue
            h=b''
            try:
                with open(p,'rb') as f: h=f.read(16)
            except Exception: pass
            rows.append((st.st_mtime,st.st_size,h.hex(),p))
for t,s,h,p in sorted(rows,reverse=True)[:300]:
    print(datetime.datetime.fromtimestamp(t).isoformat(),f'{s:14d}',h[:32],p)
print('COUNT',len(rows))

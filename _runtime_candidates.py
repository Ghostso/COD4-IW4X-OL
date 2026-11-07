import os,time,datetime,sys
roots=['D:\\BaiduNetdiskDownload\\使命召唤OL',os.environ.get('TEMP',''),os.path.expandvars(r'%LOCALAPPDATA%\\CrashDumps'),r'C:\\ProgramData\\Microsoft\\Windows\\WER']
rows=[]
for root in roots:
    if not root or not os.path.isdir(root): continue
    print('ROOT_START',root,file=sys.stderr,flush=True)
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d.lower()!='tvm0']
        for n in fn:
            if n.lower().endswith('.tvm0'): continue
            p=os.path.join(dp,n); low=n.lower()
            if not (low.endswith(('.dmp','.mdmp','.dump','.mem','.vmem','.raw','.core','.zip','.7z','.rar')) or any(k in low for k in ('dump','memory','minidump','crash','codomp','shipretail'))): continue
            try: st=os.stat(p)
            except OSError: continue
            if st.st_size<5000000: continue
            try:
                with open(p,'rb') as f: h=f.read(32)
            except Exception: h=b''
            rows.append((st.st_mtime,st.st_size,h.hex(),p))
    print('ROOT_DONE',root,len(rows),file=sys.stderr,flush=True)
for t,s,h,p in sorted(rows,reverse=True):
    print(datetime.datetime.fromtimestamp(t).isoformat(),f'{s:15d}',h,p)
print('COUNT',len(rows))

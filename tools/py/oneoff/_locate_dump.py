import os,time,datetime,sys
roots=['D:\\BaiduNetdiskDownload\\使命召唤OL',os.path.expandvars(r'%USERPROFILE%'),'D:\\','C:\\ProgramData\\Microsoft\\Windows\\WER',os.path.expandvars(r'%LOCALAPPDATA%\\CrashDumps')]
cut=time.time()-2*86400
seen=set(); rows=[]
skip_dirs={'.git','node_modules','__pycache__','.vscode','.nuget','.cache','Cache','Code Cache','GPUCache','WER'}
for root in roots:
    if not root or not os.path.isdir(root): continue
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d not in skip_dirs and d.lower()!='tvm0' and not os.path.islink(os.path.join(dp,d))]
        for n in fn:
            if n.lower().endswith('.tvm0'): continue
            low=n.lower(); p=os.path.join(dp,n)
            try: st=os.stat(p)
            except OSError: continue
            if st.st_size < 5000000: continue
            ext=os.path.splitext(low)[1]
            recent=st.st_mtime>=cut
            named=any(k in low for k in ('dump','memory','minidump','crash','codomp','shipretail'))
            dump_ext=ext in ('.dmp','.mdmp','.dump','.mem','.vmem','.raw','.core')
            if not (recent or named or dump_ext): continue
            key=os.path.normcase(os.path.abspath(p))
            if key in seen: continue
            seen.add(key)
            try:
                with open(p,'rb') as f: head=f.read(16)
            except Exception: head=b''
            rows.append((st.st_mtime,st.st_size,head.hex(),p))
    print('ROOT_DONE',root,'rows',len(rows),file=sys.stderr,flush=True)
for t,s,h,p in sorted(rows,reverse=True):
    print(datetime.datetime.fromtimestamp(t).isoformat(),f'{s:15d}',h[:32],p)
print('COUNT',len(rows))

import os,time,datetime
roots=[os.path.expandvars(r'%USERPROFILE%\Downloads'),os.path.expandvars(r'%USERPROFILE%\Desktop'),os.path.expandvars(r'%USERPROFILE%\Documents'),os.environ.get('TEMP'),os.path.expandvars(r'%LOCALAPPDATA%\CrashDumps')]
for r in roots:
    print('\nDIR',r)
    if not r or not os.path.isdir(r): print(' MISSING'); continue
    try: names=os.listdir(r)
    except Exception as e: print(' ERR',e); continue
    rows=[]
    for n in names:
        p=os.path.join(r,n)
        try: st=os.stat(p)
        except OSError: continue
        if os.path.isfile(p):
            rows.append((st.st_mtime,st.st_size,p))
    for t,s,p in sorted(rows,reverse=True)[:80]:
        if s>=1048576 or any(k in os.path.basename(p).lower() for k in ('dump','memory','minidump','crash','codomp','shipretail')):
            print(datetime.datetime.fromtimestamp(t).isoformat(),f'{s:14d}',p)

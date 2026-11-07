import os, hashlib, time
root=os.getcwd()
suffixes={'.pdb','.dmp','.mdmp','.minidump','.dump','.mem','.vmem','.raw','.core','.dat'}
keys=('dump','minidump','memory','memdump','procdump','pdb','symbol')
rows=[]
t0=time.time()
for base,dirs,files in os.walk(root):
    # metadata-only inventory; do not traverse huge asset payload directories recursively beyond listing
    for name in files:
        p=os.path.join(base,name); low=name.lower()
        if low.endswith(tuple(suffixes)) or any(k in low for k in keys):
            try:
                st=os.stat(p)
            except OSError:
                continue
            rows.append((st.st_size,os.path.relpath(p,root),st.st_mtime))
    if time.time()-t0>60:
        print('WALK_TIMEOUT_AT',base); break
for size,rel,mt in sorted(rows,key=lambda x:x[1].lower()):
    print(f'{size:12d} {time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(mt))} {rel}')
print('COUNT',len(rows),'SECONDS',round(time.time()-t0,2))

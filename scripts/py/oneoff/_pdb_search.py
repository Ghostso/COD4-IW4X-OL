import os,glob
roots=[]
for r in (os.path.expandvars(r'%USERPROFILE%'),r'C:\Symbols',r'C:\ProgramData\dbg\sym',r'C:\ProgramData\Microsoft\Symbols',os.path.expandvars(r'%LOCALAPPDATA%\Temp\SymbolCache')):
    if r and os.path.isdir(r) and r not in roots: roots.append(r)
print('ROOTS',roots)
h=[]
for root in roots:
    for dp,dn,fn in os.walk(root):
        # avoid huge/generated dirs that cannot plausibly be symbol store? still inspect all names
        for n in fn:
            if n.lower().endswith('.pdb'):
                p=os.path.join(dp,n)
                try: st=os.stat(p)
                except OSError: continue
                h.append((st.st_size,st.st_mtime,p))
print('PDB_COUNT',len(h))
for s,t,p in sorted(h,reverse=True): print(s,p)

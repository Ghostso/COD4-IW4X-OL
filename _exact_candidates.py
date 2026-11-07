import os
root=os.getcwd()
print("cwd",root)
for base,dirs,files in os.walk(root):
    for name in files:
        low=name.lower()
        if low.endswith((".pdb",".dmp",".mdmp",".minidump",".dump",".mem",".vmem",".raw",".core")):
            p=os.path.join(base,name)
            try: st=os.stat(p)
            except OSError: continue
            print(st.st_size,os.path.relpath(p,root))

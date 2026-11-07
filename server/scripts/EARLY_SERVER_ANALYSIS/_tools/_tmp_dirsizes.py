import os
root = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server"
def size(p):
    n=0; b=0
    for dp,_,fs in os.walk(p):
        for f in fs:
            fp=os.path.join(dp,f)
            try: b+=os.path.getsize(fp); n+=1
            except OSError: pass
    return n,b
tops = sorted(os.listdir(root))
rows=[]
for t in tops:
    p=os.path.join(root,t)
    if os.path.isdir(p):
        n,b=size(p); rows.append((t,n,b/1048576))
rows.sort(key=lambda r:-r[2])
for t,n,mib in rows: print(f"{t}\t{n}\t{mib:.2f} MiB")
print("--- subtrees ---")
for t in ["dedicated","lobby","build"]:
    p=os.path.join(root,t)
    for sub in sorted(os.listdir(p)):
        sp=os.path.join(p,sub)
        if os.path.isdir(sp):
            n,b=size(sp); print(f"{t}/{sub}\t{n}\t{b/1048576:.2f} MiB")

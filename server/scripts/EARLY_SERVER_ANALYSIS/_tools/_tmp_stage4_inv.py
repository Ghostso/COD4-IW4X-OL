# -*- coding: utf-8 -*-
import os, io
srv = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server"
def count(d):
    n=0; sz=0
    for r,_,fs in os.walk(d):
        for f in fs:
            n+=1
            try: sz+=os.path.getsize(os.path.join(r,f))
            except: pass
    return n,sz
for sub in ("dedicated","lobby","patcher","tools","resource","build"):
    p=os.path.join(srv,sub)
    if os.path.isdir(p):
        n,sz=count(p); print(f"{sub}: {n} files, {sz/1048576:.2f} MiB")
print("=== dedicated/src subdirs ===")
p=os.path.join(srv,"dedicated","src")
for e in sorted(os.listdir(p)):
    fp=os.path.join(p,e)
    if os.path.isdir(fp):
        n,sz=count(fp); print(f"  {e}: {n} files, {sz/1048576:.2f} MiB")
    else:
        print(f"  [file] {e}")
print("=== dedicated/src/codol ===")
p=os.path.join(srv,"dedicated","src","codol")
if os.path.isdir(p):
    for e in sorted(os.listdir(p)):
        fp=os.path.join(p,e)
        if os.path.isdir(fp):
            n,sz=count(fp); print(f"  {e}: {n} files, {sz/1048576:.2f} MiB")
        else:
            print(f"  [file] {e}")

# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
b=open(IMG,"rb").read()
def ctx(tok, k=6, w=40):
    print("### %r"%tok)
    s=0;n=0
    while True:
        j=b.find(tok,s)
        if j<0:break
        print("  @%08X %r"%(j,b[max(0,j-w):j+len(tok)+w]))
        s=j+1;n+=1
        if n>=k:break
    if n==0: print("  (none)")
for t in [b"recv",b"RECV",b"select",b"SELECT",b"WIN_FILE_READ_ERROR",b"ReadFileEx",b"SleepEx",b"OVERLAPPED",b"overlapped"]:
    ctx(t,4)

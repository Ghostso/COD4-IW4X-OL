#!/usr/bin/env python3
import os
def show(path,lo,hi,label):
    d=open(path,"rb").read(); N=len(d)
    lo=max(0,lo);hi=min(N,hi)
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=d[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()
E=r"E:\codol_re\client_image_20261027.bin"
EXE=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
show(E,0x9B6A80,0x9B6C40,"E_image nQlo ctx")
show(EXE,0x6A2A80,0x6A2C40,"EXE nQlo ctx")

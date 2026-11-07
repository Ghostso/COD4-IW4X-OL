#!/usr/bin/env python3
import os
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N=len(data)
def show(lo,hi,label):
    lo=max(0,lo); hi=min(N,hi)
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=data[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()

for off in [0x35C5AA5,0x35CDB0B,0x35F7217,0x36E1515,0x36E1641]:
    show(off-0x90, off+0x70, "DWServiceStatus @0x%X"%off)

# marketplace @0x35CDAF7 ctx
show(0x35CDA80,0x35CDB60,"marketplace+DWServiceStatus")

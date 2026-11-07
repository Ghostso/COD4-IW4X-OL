#!/usr/bin/env python3
import re
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
show(0x361E400,0x361E800,"ServiceManager/ServiceID area")
show(0x352FA00,0x352FB00,"ServiceManager const area")

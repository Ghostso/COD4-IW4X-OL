#!/usr/bin/env python3
import struct
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()

def show(o, pre=0x80, post=0x180):
    lo=max(0,o-pre); hi=min(len(data),o+post)
    seg=data[lo:hi]
    print("--- @0x%X (pre=0x%X) ---"%(o,pre))
    for i in range(0,len(seg),16):
        chunk=seg[i:i+16]
        hexs=" ".join("%02x"%b for b in chunk)
        txt="".join(chr(b) if 32<=b<127 else "." for b in chunk)
        print("  0x%08X  %-47s  %s"%(lo+i,hexs,txt))
    print()

# 所有服务名共同出现处 (0x352FA00-0x352FC00)
show(0x352FA00, 0, 0x260)

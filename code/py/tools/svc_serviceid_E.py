#!/usr/bin/env python3
import struct
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()

def show(o, pre=0x80, post=0x180, label=""):
    lo=max(0,o-pre); hi=min(len(data),o+post)
    seg=data[lo:hi]
    print("=== %s @0x%X ==="%(label,o))
    for i in range(0,len(seg),16):
        chunk=seg[i:i+16]
        hexs=" ".join("%02x"%b for b in chunk)
        txt="".join(chr(b) if 32<=b<127 else "." for b in chunk)
        print("  0x%08X  %-47s  %s"%(lo+i,hexs,txt))
    print()

# ServiceID 各出现处
for o in [0x32F1BF3, 0x33D7FD6, 0x33D800E, 0x33D812A, 0x33D8146, 0x33D8150]:
    show(o, 0x80, 0x120, "ServiceID")

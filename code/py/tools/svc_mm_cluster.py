#!/usr/bin/env python3
import struct
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()

def show(lo, hi, label=""):
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo, hi, 16):
        chunk=data[i:i+16]
        hexs=" ".join("%02x"%b for b in chunk)
        txt="".join(chr(b) if 32<=b<127 else "." for b in chunk)
        print("  0x%08X  %-47s  %s"%(i,hexs,txt))
    print()

show(0x9DF180, 0x9DF2C0, "matchmaking cluster")
show(0x9D9D80, 0x9D9E20, "matchmaking 2")

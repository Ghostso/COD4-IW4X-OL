#!/usr/bin/env python3
import struct
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()
N=len(data)

def show(lo, hi, label=""):
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo, hi, 16):
        chunk=data[i:i+16]
        hexs=" ".join("%02x"%b for b in chunk)
        txt="".join(chr(b) if 32<=b<127 else "." for b in chunk)
        print("  0x%08X  %-47s  %s"%(i,hexs,txt))
    print()

for needle in [b"pooledstorage", b"publisher_storage", b"publisherstorage"]:
    i=0
    while True:
        p=data.find(needle,i)
        if p<0: break
        i=p+1
        print("FOUND %r @0x%X"%(needle,p))
        show(max(0,p-0x120), p+0x120, needle.decode())
        break

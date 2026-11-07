#!/usr/bin/env python3
import struct
def dump(path, lo, hi, label):
    data=open(path,"rb").read()
    lo=max(0,lo); hi=min(len(data),hi)
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=data[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()

E=r"E:\codol_re\client_image_20261027.bin"
dump(E, 0xA6AE00, 0xA6AF40, "bdMessaging")
dump(E, 0x9D5000, 0x9D50C0, "InstantMessage")
dump(E, 0x3320F00, 0x3320FD0, "Storage2")

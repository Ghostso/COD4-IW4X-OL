#!/usr/bin/env python3
import struct
E=r"E:\codol_re\client_image_20261027.bin"
data=open(E,"rb").read()
off=0x0722EC00
print("=== file0x%X window 512B ==="%off)
for i in range(off,off+512,16):
    c=data[i:i+16]
    print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
          "".join(chr(b) if 32<=b<127 else "." for b in c)))
print("\nu32 seq:")
print([struct.unpack_from("<I",data,off+k)[0] for k in range(0,256,4)])

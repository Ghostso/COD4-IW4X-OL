# -*- coding: utf-8 -*-
import struct
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()


def rd(rva, n=16):
    return d[rva:rva + n]


for label, rva in [("EXPORT", 0x00A155B0), ("IMPORT", 0x0E5DC635),
                   ("SECURITY", 0x00777048), ("DEBUG", 0x008ADA60),
                   ("TLS", 0x009E8EB8), ("RES", 0x0E5C9000),
                   ("Entry", 0x0E5DC690)]:
    print("%-9s RVA 0x%08X bytes %s" % (label, rva, rd(rva).hex(" ")))

print()
o = 0x00A155B0
f = struct.unpack_from("<IIHHIIIIIII", d, o)
names = ["Char", "TimeDate", "MajV", "MinV", "Name", "Base", "NF", "NN",
         "AF", "AN", "AO"]
for k, v in zip(names, f):
    print("  EXPORT %-9s 0x%08X" % (k, v))
nv = f[4]
print("  Name RVA 0x%08X -> %r" % (nv, d[nv:nv + 64].split(b"\x00")[0]))

print()
o = 0x009E8EB8
print("  TLS raw:", d[o:o + 0x18].hex(" "))
print("  TLS:", ["0x%08X" % struct.unpack_from("<I", d, o + i)[0]
                 for i in range(0, 0x18, 4)])

print()
print("  Entry raw:", d[0x0E5DC690:0x0E5DC6B0].hex(" "))
print("  Import raw:", d[0x0E5DC635:0x0E5DC665].hex(" "))

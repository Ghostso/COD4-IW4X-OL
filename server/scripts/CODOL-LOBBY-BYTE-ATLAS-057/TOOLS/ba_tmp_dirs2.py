# -*- coding: utf-8 -*-
import struct
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()


def cstr(rva):
    return d[rva:d.find(b"\x00", rva)].decode("latin1", "replace")


EXPORT = 0x00A155B0
f = struct.unpack_from("<IIHHIIIIIII", d, EXPORT)
NF, NN, AF, AN, AO, BASEIDX = f[6], f[7], f[8], f[9], f[10], f[5]
print("=== 导出表: %d 函数 / %d 名字, ordinal base=%d ===" % (NF, NN, BASEIDX))
funcs = [struct.unpack_from("<I", d, AF + i * 4)[0] for i in range(NF)]
names = [struct.unpack_from("<I", d, AN + i * 4)[0] for i in range(NN)]
ords = [struct.unpack_from("<H", d, AO + i * 2)[0] for i in range(NN)]
for i in range(NN):
    print("  [%2d] ord=%d rva=0x%08X  %s"
          % (i, ords[i] + BASEIDX, funcs[ords[i]], cstr(names[i])))

print()
print("=== TLS 目录 ===")
TLS = 0x009E8EB8
start_va, end_va, idx_va, cb_va = struct.unpack_from("<IIII", d, TLS)
print("  StartOfRawData VA=0x%08X  文件偏移=0x%08X" % (start_va, start_va - 0x400000))
print("  EndOfRawData   VA=0x%08X  (大小 %d 字节)" % (end_va, end_va - start_va))
print("  AddressOfIndex VA=0x%08X  值=0x%08X"
      % (idx_va, struct.unpack_from("<I", d, idx_va - 0x400000)[0]))
print("  AddressOfCallBacks VA=0x%08X" % cb_va)
p = cb_va - 0x400000
i = 0
while True:
    v = struct.unpack_from("<I", d, p)[0]
    print("    cb[%d] = 0x%08X" % (i, v))
    if v == 0 or i > 8:
        break
    p += 4
    i += 1

print()
print("=== 资源目录 RVA 0x0E5C9000 (SIZE 字段=0 但有内容) ===")
o = 0x0E5C9000
for r in range(0, 0x40, 16):
    print("  %08X  %-47s  %s" % (o + r, d[o + r:o + r + 16].hex(" "),
                                 "".join(chr(c) if 32 <= c < 127 else "."
                                         for c in d[o + r:o + r + 16])))

print()
print("=== 节 3 .tp3 @0x0E5C8000 (vsz 0x31) ===")
o = 0x0E5C8000
print("  ", d[o:o + 0x31].hex(" "))
print("  ", repr(d[o:o + 0x31]))

print()
print("=== DEBUG 目录 RVA 0x008ADA60 ===")
o = 0x008ADA60
for r in range(0, 0x1C, 4):
    print("   +0x%02X = 0x%08X" % (r, struct.unpack_from("<I", d, o + r)[0]))

print()
print("=== 安全目录 (证书表) RVA 0x00777048 size 0x35F8 ===")
o = 0x00777048
print("  前 48 字节:", d[o:o + 48].hex(" "))
dwlen, wrev, wtype = struct.unpack_from("<IHH", d, o)
print("  dwLength=%d wRevision=0x%04X wCertificateType=0x%04X"
      % (dwlen, wrev, wtype))

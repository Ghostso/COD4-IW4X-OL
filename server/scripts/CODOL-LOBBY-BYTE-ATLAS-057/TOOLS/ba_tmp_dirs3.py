# -*- coding: utf-8 -*-
import struct
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()


def cstr(off, mx=512):
    e = d.find(b"\x00", off)
    return d[off:e if e > 0 else off + mx]


def u4(off):
    return struct.unpack_from("<I", d, off)[0]


def u2(off):
    return struct.unpack_from("<H", d, off)[0]


print("=== [1] TLS 目录 (RVA=file offset) ===")
TLS = 0x009E8EB8
a, b = u4(TLS), u4(TLS + 4)
idx, cb = u4(TLS + 8), u4(TLS + 12)
print("  StartOfRawData   RVA=0x%08X" % a)
print("  EndOfRawData     RVA=0x%08X  (size %d)" % (b, b - a))
print("  AddressOfIndex   RVA=0x%08X  值=0x%08X" % (idx, u4(idx)))
print("  AddressOfCallBacks RVA=0x%08X" % cb)
p = cb
for i in range(8):
    v = u4(p)
    print("    cb[%d] = 0x%08X" % (i, v))
    if v == 0:
        break
    p += 4

print()
print("=== [2] DEBUG / CodeView ===")
DBG = 0x008ADA60
ch, ts, maj, mnr, typ, sz, addr, ptr = struct.unpack_from("<IIHHIIII", d, DBG)
print("  Characteristics=0x%X TimeDate=0x%08X(v%d.%d) Type=%d Size=%d"
      % (ch, ts, maj, mnr, typ, sz))
print("  AddressOfRawData RVA=0x%08X  PointerToRawData=0x%08X" % (addr, ptr))
for base in (addr, ptr):
    raw = d[base:base + sz]
    if raw[:4] == b"RSDS":
        print("  => RSDS @0x%08X" % base)
        print("     GUID:", raw[4:20].hex())
        print("     Age :", struct.unpack_from("<I", raw, 20)[0])
        print("     PDB :", raw[24:].split(b"\x00")[0].decode("latin1"))
    elif raw[:4] == b"NB10":
        print("  => NB10 @0x%08X" % base)
        print("     PDB :", raw[16:].split(b"\x00")[0].decode("latin1"))

print()
print("=== [3] 资源目录 (5 项) ===")
RES = 0x0E5C9000
ch, ts, maj, mnr, nn, ni = struct.unpack_from("<IIHHHH", d, RES)
print("  Characteristics=0x%X TimeDate=0x%X Ver=%d.%d Named=%d Id=%d"
      % (ch, ts, maj, mnr, nn, ni))
RESTYPE = {1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU", 5: "DIALOG",
           6: "STRINGTABLE", 9: "ACCELERATOR", 10: "RCDATA", 12: "GROUP_CURSOR",
           14: "GROUP_ICON", 16: "VERSION", 24: "MANIFEST", 3: "ICON"}
for i in range(nn + ni):
    eo = RES + 16 + i * 8
    nm, off = struct.unpack_from("<II", d, eo)
    name = nm if not (nm & 0x80000000) else "<named@0x%X>" % (nm & 0x7FFFFFFF)
    sub = off & 0x7FFFFFFF
    isdir = bool(off & 0x80000000)
    print("  [%d] id=%s off=0x%08X dir=%s %s"
          % (i, name, sub, isdir, RESTYPE.get(nm, "")))
    if not isdir:
        do = RES + sub
        rva, sz, cp = struct.unpack_from("<III", d, do)
        print("       => data RVA=0x%08X size=%d cp=%d" % (rva, sz, cp))
        blob = d[rva:rva + sz]
        if nm == 24:
            print("       MANIFEST:", blob.decode("latin1", "replace")[:400])
        elif nm == 16:
            print("       VERSION:", blob[:120].hex(" "))
    else:
        so = RES + sub
        c2, t2, m2, n2, nn2, ni2 = struct.unpack_from("<IIHHHH", d, so)
        print("       sub: Named=%d Id=%d" % (nn2, ni2))
        for j in range(nn2 + ni2):
            nm2, off2 = struct.unpack_from("<II", d, so + 16 + j * 8)
            print("         [%d] id=%d dir=%s off=0x%08X"
                  % (j, nm2, bool(off2 & 0x80000000), off2 & 0x7FFFFFFF))

# -*- coding: utf-8 -*-
"""解析 codoMP_client_shipRetailBase.dll 的 PE 身份."""
import struct
import sys

P = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d = open(P, "rb").read()
N = len(d)
print("file: %s" % P)
print("size: %d (0x%X)" % (N, N))
if d[:2] != b"MZ":
    print("NOT MZ")
    sys.exit()

e = struct.unpack_from("<I", d, 0x3C)[0]
print("e_lfanew = 0x%X" % e)
if d[e:e + 4] != b"PE\0\0":
    print("NOT PE")
    sys.exit()
coff = e + 4
mach, nsec, ts, psym, nsym, optsz, ch = struct.unpack_from("<HHIIIHH", d, coff)
print("Machine=0x%04X  NSections=%d  TimeDate=0x%08X  OptSize=0x%X  Char=0x%04X"
      % (mach, nsec, ts, optsz, ch))
import datetime
print("  TimeDate -> %s UTC" % datetime.datetime.utcfromtimestamp(ts))
opt = coff + 20
magic = struct.unpack_from("<H", d, opt)[0]
print("Magic=0x%04X (%s)" % (magic, "PE32+" if magic == 0x20B else "PE32"))
plus = magic == 0x20B
ib = struct.unpack_from("<Q" if plus else "<I", d, opt + (24 if plus else 28))[0]
aep = struct.unpack_from("<I", d, opt + 16)[0]
soi = struct.unpack_from("<I", d, opt + 56)[0]
soh = struct.unpack_from("<I", d, opt + 60)[0]
print("ImageBase=0x%016X  EntryPoint=0x%08X" % (ib, aep))
print("SizeOfImage=0x%08X  SizeOfHeaders=0x%X" % (soi, soh))
nd_off = opt + (108 if plus else 92)
nd = struct.unpack_from("<I", d, nd_off)[0]
print("NumberOfRvaAndSizes=%d" % nd)

# section table
secoff = opt + optsz
secs = []
for i in range(nsec):
    o = secoff + i * 40
    nm = d[o:o + 8].rstrip(b"\0").decode("latin1", "replace")
    vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
    c = struct.unpack_from("<I", d, o + 36)[0]
    secs.append(dict(i=i, nm=nm, va=va, vs=vs, rs=rs, rp=rp, ch=c))
print("\n节表 %d 个:" % nsec)
print("  %-3s %-10s %-12s %-12s %-12s %-12s %s"
      % ("#", "name", "VA", "VSize", "RawPtr", "RawSize", "Chars"))
for s in secs:
    print("  %-3d %-10s 0x%08X   0x%08X   0x%08X   0x%08X   0x%08X"
          % (s["i"], s["nm"], s["va"], s["vs"], s["rp"], s["rs"], s["ch"]))

print("\n节表是否首尾相接 & 是否覆盖到 SizeOfImage:")
prev = None
for s in secs:
    end = s["va"] + s["vs"]
    gap = "" if prev is None else "  间隙 %d" % (s["va"] - prev)
    print("  节%-2d [0x%08X, 0x%08X)%s" % (s["i"], s["va"], end, gap))
    prev = end
print("  末节末端 0x%08X  vs SizeOfImage 0x%08X  %s"
      % (prev, soi, "OK" if prev == soi else "MISMATCH"))

# RP 有效性
print("\nRawPtr 与 VA 是否同一文件位置:")
for s in secs:
    print("  节%-2d VA=0x%08X RawPtr=0x%08X  %s"
          % (s["i"], s["va"], s["rp"],
             "same" if s["va"] == s["rp"] else "differs"))

print("\n数据目录:")
dn = ["EXPORT", "IMPORT", "RESOURCE", "EXCEPTION", "SECURITY", "BASERELOC",
      "DEBUG", "ARCH", "GLOBALPTR", "TLS", "LOADCFG", "BOUNDIMP", "IAT",
      "DELAYIMP", "COM", "RESERVED"]
dirs = []
for i in range(min(nd, 16)):
    rva, sz = struct.unpack_from("<II", d, nd_off + 4 + i * 8)
    dirs.append((rva, sz))
    print("  [%2d] %-12s RVA=0x%08X  Size=0x%08X (%d)" % (i, dn[i], rva, sz, sz))

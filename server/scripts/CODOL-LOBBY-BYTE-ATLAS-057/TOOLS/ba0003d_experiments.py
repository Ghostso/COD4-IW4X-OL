# -*- coding: utf-8 -*-
"""BAP-0003D 的证伪实验 (修正: call/[TLS] 里的立即数是 VA, offset = VA - 0x400000)"""
import glob
import os
import struct

IMG = r"E:\codol_re\client_image_20261027.bin"
BASE = 0x400000
d = open(IMG, "rb").read()
N = len(d)


def rd(va, n=16):
    o = va - BASE
    return d[o:o + n] if 0 <= o < N else b""


def u4_va(va):
    o = va - BASE
    return struct.unpack_from("<I", d, o)[0] if 0 <= o < N - 4 else None


print("image size 0x%X -> VA range 0x%08X .. 0x%08X"
      % (N, BASE, BASE + N))

print()
print("=" * 70)
print("实验 E1: 入口点跳板 call [VA 0x0E9DC665]")
print("=" * 70)
print("  [VA 0x0E9DC665] =", hex(u4_va(0x0E9DC665)) if u4_va(0x0E9DC665) is not None else "OUT")
print("  [VA 0x0E9DC664] = 0x%08X" % u4_va(0x0E9DC664))
print("  [VA 0x0E9DC660] = 0x%08X" % u4_va(0x0E9DC660))
print()
print("  槽附近 (VA 0x0E9DC640 .. 0x0E9DC6A0):")
for va in range(0x0E9DC640, 0x0E9DC6A0, 16):
    print("    %08X  %-47s  %s"
          % (va, rd(va, 16).hex(" "),
             "".join(chr(c) if 32 <= c < 127 else "." for c in rd(va, 16))))

print()
print("=" * 70)
print("实验 E1b: 入口点前后")
print("=" * 70)
for va in range(0x0E5DC650, 0x0E5DC710, 16):
    print("  %08X  %-47s  %s"
          % (va, rd(va, 16).hex(" "),
             "".join(chr(c) if 32 <= c < 127 else "." for c in rd(va, 16))))

print()
print("=" * 70)
print("实验 E1c: 追踪 call 目标")
print("=" * 70)
t = u4_va(0x0E9DC665)
if t:
    print("  target VA = 0x%08X  (offset 0x%08X)" % (t, t - BASE))
    for va in range(t & ~0xF, (t & ~0xF) + 0x50, 16):
        print("    %08X  %-47s  %s"
              % (va, rd(va, 16).hex(" "),
                 "".join(chr(c) if 32 <= c < 127 else "." for c in rd(va, 16))))

print()
print("=" * 70)
print("实验 E1d: TLS (字段是 VA)")
print("=" * 70)
TLS = 0x009E8EB8
for k, off in (("StartOfRawData", 0), ("EndOfRawData", 4),
               ("AddressOfIndex", 8), ("AddressOfCallBacks", 12)):
    va = struct.unpack_from("<I", d, TLS + off)[0]
    print("  %-20s VA=0x%08X offset=0x%08X %s"
          % (k, va, va - BASE,
             "IN" if 0 <= va - BASE < N else "OUT-OF-IMAGE"))

print()
print("=" * 70)
print("实验 E2/E3: 磁盘原始 EXE")
print("=" * 70)
root = r"D:\BaiduNetdiskDownload\使命召唤OL"
seen = set()
for p in ("**/codoMP_client_shipRetail.exe", "**/codo*.exe", "**/CoD*.exe"):
    for f in glob.glob(os.path.join(root, p), recursive=True):
        try:
            sz = os.path.getsize(f)
        except OSError:
            continue
        if f not in seen:
            seen.add(f)
            print("  %12d  %s" % (sz, f))
print("  found: %d" % len(seen))

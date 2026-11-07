# -*- coding: utf-8 -*-
"""BAP-0005 取证: SECURITY 目录 / TLS 回调 / 各目录真实字节."""
import struct

IMG = r"E:\codol_re\client_image_20261027.bin"
d = open(IMG, "rb").read()
N = len(d)
BASE = 0x400000


def hx(off, n=16):
    return d[off:off + n].hex(" ") if 0 <= off < N else "OUT"


def asc(off, n=16):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in d[off:off + n])


print("=" * 74)
print("[A] SECURITY 目录 声明 RVA=0x00777048 Size=0x35F8")
print("=" * 74)
S = 0x00777048
print("  首 32 字节: %s" % hx(S, 32))
print("  ASCII     : %s" % asc(S, 32))
print("  若作为 WIN_CERTIFICATE: dwLength=0x%08X wRevision=0x%04X wType=0x%04X"
      % (struct.unpack_from("<I", d, S)[0],
         struct.unpack_from("<H", d, S + 4)[0],
         struct.unpack_from("<H", d, S + 6)[0]))
print("  该位置所在节: ", end="")
for s in (("节0", 0x00001000, 0x008A689A), ("节1", 0x008A8000, 0x0016DA70),
          ("节2", 0x00A16000, 0x0DBB1CC0), ("节5", 0x0E5D3000, 0x00004000),
          ("节6", 0x0E5D7000, 0x00082000)):
    if s[1] <= S < s[1] + s[2]:
        print("%s (代码? %s)" % (s[0], s[0] in ("节0", "节5")))
        break
else:
    print("?")
print()
print("  —— 全文件里有没有真的 WIN_CERTIFICATE (wRevision==0x0200)? ——")
found = 0
for off in range(0, N - 8, 4):
    rev = struct.unpack_from("<H", d, off + 4)[0]
    if rev == 0x0200:
        ln = struct.unpack_from("<I", d, off)[0]
        ty = struct.unpack_from("<H", d, off + 6)[0]
        if 8 < ln < 0x100000 and ty in (1, 2, 3, 4):
            print("    @0x%08X len=%d rev=0x0200 type=%d  %s"
                  % (off, ln, ty, hx(off, 16)))
            found += 1
            if found > 10:
                break
print("    合计 %d 个候选" % found)

print()
print("=" * 74)
print("[B] TLS 回调表 AddressOfCallBacks = VA 0x00CADA3C -> RVA 0x008ADA3C")
print("=" * 74)
CB = 0x00CADA3C - BASE
print("  file_offset = 0x%08X" % CB)
for r in range(0, 0x40, 16):
    o = CB + r
    print("    %08X  %-47s  %s" % (o, hx(o, 16), asc(o, 16)))
print()
print("  逐项 (指针应为 VA):")
p = CB
for i in range(8):
    v = struct.unpack_from("<I", d, p)[0]
    print("    cb[%d] = 0x%08X  %s" % (i, v, "" if v == 0 else
                                       "-> RVA 0x%08X %s" % (v - BASE,
                                                             hx(v - BASE, 12))))
    if v == 0:
        break
    p += 4

print()
print("=" * 74)
print("[C] TLS 模板数据 StartOfRawData VA 0x0E9C8000 -> RVA 0x0E5C8000")
print("=" * 74)
T = 0x0E9C8000 - BASE
print("  file_offset = 0x%08X  (节3, 48 字节)" % T)
print("  内容: %s" % hx(T, 48))

print()
print("=" * 74)
print("[D] AddressOfIndex VA 0x0196930C -> RVA 0x0156930C")
print("=" * 74)
IDX = 0x0196930C - BASE
print("  file_offset = 0x%08X %s" % (IDX, "IN" if IDX < N else "OUT"))
print("  当前值: 0x%08X (运行时写入)" % struct.unpack_from("<I", d, IDX)[0]
      if IDX < N - 4 else "  OUT")

print()
print("=" * 74)
print("[E] DEBUG 目录 CodeView 完整")
print("=" * 74)
DBG = 0x008ADA60
ch, ts, maj, mnr, typ, sz, addr, ptr = struct.unpack_from("<IIHHIIII", d, DBG)
print("  Type=%d SizeOfData=%d  AddressOfRawData(RVA)=0x%08X" % (typ, sz, addr))
raw = d[addr:addr + sz]
print("  RSDS 签名: %r" % raw[:4])
print("  GUID     : %s" % raw[4:20].hex())
print("  Age      : %d" % struct.unpack_from("<I", raw, 20)[0])
print("  PDB      : %r" % raw[24:].split(b"\x00")[0].decode("latin1"))

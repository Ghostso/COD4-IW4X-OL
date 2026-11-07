# -*- coding: utf-8 -*-
"""BAP-0004 取证: 镜像覆盖缺口 + 节别名 + 导入表真实结构."""
import struct

IMG = r"E:\codol_re\client_image_20261027.bin"
d = open(IMG, "rb").read()
N = len(d)
BASE = 0x400000

print("=" * 72)
print("[1] 镜像覆盖缺口")
print("=" * 72)
print("  文件长度       = 0x%08X  (%d)" % (N, N))
print("  SizeOfImage    = 0x0E659000")
print("  若有 VA→off = VA-0x400000, 可覆盖到 VA 0x%08X" % (BASE + N))
print("  SizeOfImage    = 0x%08X" % 0x0E659000)
print("  缺口           = 0x%08X 字节" % (0x0E659000 - (BASE + N)))
print()
print("  => 入口点 call [0x0E9DC665] 的槽在 VA 0x0E9DC665,")
print("     可映射上限 VA 0x0EA59000, 槽在范围内.")
print("     但 0x0E9DC665-0x400000 = 0x0E5DC665 < 0x0E659000 也在范围内.")
print("     ★ 关键: 0x0E5DC665 处读到的是 'codoMP_client_shipRetailBase.dll'")
print("       字符串中间 (0x0E5DC66D 是该串起点), 所以 0x0E5DC665 不是槽.")
print("       这说明 [0x0E9DC665] 是 VA 而非 RVA, 而 VA-0x400000 = 0x0E5DC665")
print("       ★ 这正好是字符串区 -> 该槽本身可能就是一个字符串常量地址?")

print()
print("=" * 72)
print("[2] 节别名: 检查 3..6 的 RawPtr 是否与 VA 内容一致")
print("=" * 72)
e = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, e + 6)[0]
optsz = struct.unpack_from("<H", d, e + 20)[0]
opt = e + 24
secoff = opt + optsz
secs = []
for i in range(nsec):
    o = secoff + i * 40
    nm = d[o:o + 8].rstrip(b"\0").decode("latin1")
    vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
    secs.append((i, nm, va, vs, rp, rs))

for i, nm, va, vs, rp, rs in secs:
    same_at_va = d[va:va + min(vs, 64)] if va + 64 <= N else b""
    same_at_rp = d[rp:rp + min(rs, 64)] if rp + 64 <= N else b""
    eq = same_at_va[:32] == same_at_rp[:32]
    print("  节%d %-6s VA=0x%08X RawPtr=0x%08X  VA==RawPtr内容? %s"
          % (i, nm, va, rp, "YES" if eq else "NO"))
    if not eq:
        print("      @VA  : %s" % same_at_va[:32].hex(" "))
        print("      @Raw : %s" % same_at_rp[:32].hex(" "))

print()
print("=" * 72)
print("[3] 导入表真实结构 (RVA 0x0E5DC635)")
print("=" * 72)
IMP = 0x0E5DC635


def cstr(off, mx=256):
    e2 = d.find(b"\x00", off, off + mx)
    return d[off:e2].decode("latin1", "replace") if e2 > 0 else "?"


i = 0
p = IMP
while True:
    oft, ts, fwd, name, ft = struct.unpack_from("<IIIII", d, p)
    if oft == 0 and name == 0 and ft == 0:
        print("  [%d] 终止描述符 (全零 @0x%08X)" % (i, p))
        break
    print("  [%d] @0x%08X  OFT=0x%08X Name=0x%08X FT=0x%08X  \"%s\""
          % (i, p, oft, name, ft, cstr(name)))
    for lbl, thunk in (("OFT", oft), ("FT", ft)):
        if not thunk:
            continue
        for thunk_va in (thunk, thunk - BASE):
            if 0 <= thunk_va < N - 4:
                v = struct.unpack_from("<I", d, thunk_va)[0]
                if v and v != 0xFFFFFFFF:
                    print("      %s 作为file_off 0x%08X -> 首项 0x%08X"
                          % (lbl, thunk_va, v))
    p += 20
    i += 1
    if i > 40:
        print("  ... (超过 40 项)")
        break

print()
print("=" * 72)
print("[4] 节表原始字节 (检查我的 COFF/可选头解析是否偏移)")
print("=" * 72)
print("  e_lfanew        = 0x%08X" % e)
print("  COFF.NumSections= %d" % nsec)
print("  COFF.OptSize    = 0x%X" % optsz)
print("  可选头 Magic    = 0x%04X" % struct.unpack_from("<H", d, opt)[0])
print("  节表起点        = 0x%08X" % secoff)
for r in range(0, nsec * 40 + 16, 16):
    o = secoff + r
    print("    %08X  %-47s  %s"
          % (o, d[o:o + 16].hex(" "),
             "".join(chr(c) if 32 <= c < 127 else "." for c in d[o:o + 16])))

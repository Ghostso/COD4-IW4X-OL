#!/usr/bin/env python3
"""${CODO_*} 宏替换表: 0x0B6A8C / 0x0B6D32 附近的结构.
假设: 一张 {宏名ptr, 值ptr, 值长度} 的静态表, 被 vtable 方法调用.
列出 0x9B79C0..0x9B7A80 的串(宏名) 与 0xB6xxx 的引用点, 并反汇编 0xB6CC0..0xB6DA0.
"""
import struct, re, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

def cstr(off, ml=200):
    if not (0 <= off < N): return None
    e = d.find(b"\x00", off)
    if e < 0 or e - off > ml: e = off + ml
    return d[off:e]

out("=== 0x9B79A0..0x9B7B00 strings (macro names region) ===")
i = 0x9B79A0
while i < 0x9B7B00:
    if 32 <= d[i] < 127 and (i == 0 or not (32 <= d[i-1] < 127)):
        e = d.find(b"\x00", i, 0x9B7B00)
        if e < 0: break
        out("  0x%06X  len=%d  %r" % (i, e - i, d[i:e].decode("latin1")))
        i = e + 1
    else:
        i += 1

out("")
out("=== 每个 ${CODO_*} 宏名 ptr 的引用点 ===")
for m in re.finditer(rb"\$\{CODO_[A-Z_]+\}", d):
    off = m.start()
    e = d.find(b"\x00", off)
    ptr = off + VA
    hits = [mm.start() for mm in re.finditer(re.escape(struct.pack("<I", ptr)), d)]
    out("  %-22s 0x%06X refs=%d %s" % (d[off:e].decode(), off, len(hits), [hex(h) for h in hits]))

out("")
out("=== disasm 0xB6CC0..0xB6DA0 ===")
code = d[0xB6CC0:0xB6DA0]
for ins in md.disasm(code, 0xB6CC0 + VA):
    line = "  0x%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
    for m in re.finditer(r"0x([0-9a-f]{6,8})", ins.op_str):
        v = int(m.group(1), 16)
        if VA <= v < VA + N:
            s = cstr(v - VA, 80)
            if s and all(32 <= c < 127 for c in s):
                line += "   ; %r" % s.decode("latin1")
    out(line)

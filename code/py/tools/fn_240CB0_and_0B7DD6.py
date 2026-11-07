#!/usr/bin/env python3
"""追 128 卷两个未闭合点:
   (a) 0x240CB0 那一支函数到底是什么 (引擎 0x640AB0 的邻居)
   (b) 0x0B7DD6 处的 ${TIMESTAMP} 引用点归属哪个函数/事件
输出: 函数边界(前向找 ret + 55 8b ec), 区内所有 push imm32 -> 串, 以及调用点。
"""
import struct, re, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

def cstr(off, ml=400):
    if not (0 <= off < N): return None
    e = d.find(b"\x00", off)
    if e < 0 or e - off > ml: e = off + ml
    return d[off:e]

def annot(ins):
    line = "  0x%08X %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
    for m in re.finditer(r"0x([0-9a-f]{6,8})", ins.op_str):
        v = int(m.group(1), 16)
        if VA <= v < VA + N:
            t = cstr(v - VA, 200)
            if t and len(t) >= 2 and all(32 <= c < 127 for c in t):
                line += "   ; %r" % t.decode("latin1")[:90]
    return line

md = Cs(CS_ARCH_X86, CS_MODE_32)

def dump(name, foff, length):
    out("=" * 78)
    out("### %s   file=0x%06X  VA=0x%08X  len<=0x%X" % (name, foff, foff + VA, length))
    out("=" * 78)
    code = d[foff:foff + length]
    for ins in md.disasm(code, foff + VA):
        out(annot(ins))

def prologues(foff_a, foff_b):
    out("--- 前向找 55 8b ec (函数入口) 于 0x%06X..0x%06X ---" % (foff_a, foff_b))
    for k in range(foff_a, foff_b):
        if d[k:k+3] == b"\x55\x8b\xec":
            out("   prologue @0x%06X (VA 0x%08X)" % (k, k + VA))

print_fn = out

# ---- (a) 0x240CB0 ----
out("############ (a) 引擎邻居 0x240CB0 ############")
prologues(0x240A00, 0x241600)
dump("0x240AB0 尾 + 0x240CB0 起 0x300", 0x240C40, 0x2C0)

out("")
out("--- 0x240700..0x241200 区里所有 push imm32 -> 字符串 ---")
for h in range(0x240700, 0x241300):
    if d[h] == 0x68:
        v = struct.unpack_from("<I", d, h + 1)[0]
        if VA <= v < VA + N:
            t = cstr(v - VA, 200)
            if t and len(t) >= 3 and all(32 <= c < 127 for c in t):
                out("   push@0x%06X -> 0x%06X %r" % (h, v - VA, t.decode("latin1")[:100]))

# ---- (b) 0x0B7DD6 ----
out("")
out("############ (b) ${TIMESTAMP} 引用点 0x0B7DD6 ############")
prologues(0x0B7600, 0x0B7E20)
dump("0x0B7600..0x0B7E20 反汇编", 0x0B7600, 0x220)

out("")
out("--- 0x0B7C80..0x0B7E20 的 push imm32 -> 串 ---")
for h in range(0x0B7C80, 0x0B7E20):
    if d[h] == 0x68:
        v = struct.unpack_from("<I", d, h + 1)[0]
        if VA <= v < VA + N:
            t = cstr(v - VA, 300)
            if t and len(t) >= 3 and all(32 <= c < 127 for c in t):
                out("   push@0x%06X -> 0x%06X %r" % (h, v - VA, t.decode("latin1")[:120]))

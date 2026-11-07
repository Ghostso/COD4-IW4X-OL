#!/usr/bin/env python3
"""138: 递归向上追房间消息缓冲区的来源链。
从 0x634870 出发，逐层找 E8 调用者 + 该函数的入口。
用法: python -X utf8 tools/s138_upchain.py <VA> [depth]
"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=100):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def callers(t):
    pat = b"\xe8"
    out = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        if i + 5 <= N:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if VA + i + 5 + rel == t:
                out.append(VA + i)
        i += 1
    return out


def entry_of(va):
    f = va - VA
    i = f
    while i > 1:
        if d[i - 1] == 0xCC and d[i - 2] == 0xCC:
            return VA + i
        i -= 1
    return None


def dis(va, n=0x50):
    code = d[va - VA:va - VA + n]
    for ins in md.disasm(code, va):
        line = "      0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(),
                                              ins.mnemonic, ins.op_str)
        for tok in ins.op_str.replace(",", " ").split():
            if tok.startswith("0x"):
                try:
                    s = cstr(int(tok, 16))
                except ValueError:
                    continue
                if s:
                    line += "   ; '%s'" % s
        print(line)
        if ins.mnemonic.startswith("ret"):
            break


seen = set()


def up(t, depth, maxd):
    if depth > maxd or t in seen:
        return
    seen.add(t)
    cs = callers(t)
    ent = entry_of(t)
    print("\n%s 0x%08X (函数入口 0x%08X) <- %d 个调用者"
          % ("  " * depth, t, ent or 0, len(cs)))
    for c in cs:
        ce = entry_of(c)
        print("%s   call@0x%08X (在函数 0x%08X)" % ("  " * depth, c, ce or 0))
        if depth < 2:
            dis(ce or c, 0x60)
    for c in cs:
        ce = entry_of(c)
        if ce and ce != t:
            up(ce, depth + 1, maxd)


if __name__ == "__main__":
    t = int(sys.argv[1], 0)
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    up(t, 0, depth)

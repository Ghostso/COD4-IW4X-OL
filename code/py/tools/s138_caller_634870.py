#!/usr/bin/env python3
"""138: 找 0x634870(房间消息解包派发) 的调用者，以及它拿的缓冲区从哪来。"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=120):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def callers(target_va):
    pat = b"\xe8"
    out = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        if i + 5 <= N:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if VA + i + 5 + rel == target_va:
                out.append(VA + i)
        i += 1
    return out


def show(va, before, after, title):
    print("=" * 76)
    print(title)
    print("=" * 76)
    start = va - before
    code = d[start - VA:start - VA + before + after]
    for ins in md.disasm(code, start):
        mark = "  <<<" if ins.address == va else ""
        line = "  0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str)
        for tok in ins.op_str.replace(",", " ").split():
            if tok.startswith("0x"):
                try:
                    s = cstr(int(tok, 16))
                except ValueError:
                    continue
                if s:
                    line += "   ; '%s'" % s
        print(line + mark)


if __name__ == "__main__":
    tgt = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x634870
    cs = callers(tgt)
    print("E8 调用点 -> 0x%08X : %d 个" % (tgt, len(cs)))
    for c in cs:
        print("   0x%08X" % c)
    # 也找间接引用（函数指针表）
    pat = struct.pack("<I", tgt)
    hits = []
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        hits.append(VA + i)
    print("\n作为 imm32/指针 出现: %d 处" % len(hits))
    for h in hits[:20]:
        print("   0x%08X   上下文: %s" % (h, d[h - VA - 8:h - VA + 8].hex()))
    for c in cs[:3]:
        show(c, 0x60, 0x20, "caller @0x%08X" % c)

#!/usr/bin/env python3
"""s138_ref: 全镜像搜索一个 32 位绝对地址(或任意 4 字节模式)的所有引用，
并对每个命中点反汇编前后上下文，粗判读/写/ lea(取址)。
用法:
  python -I tools\\s138_ref.py <addr_hex> [--win N] [--all]
    addr_hex 可写 0x76446B0 或 076446b0
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


def hits(target):
    pat = struct.pack("<I", target)
    out = []
    i = 0
    while True:
        j = d.find(pat, i)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out


def classify(insn_text, mn, ops):
    # heuristic
    if mn == "mov" and ops.startswith("dword ptr [") and "," in ops:
        dst, src = ops.split(",", 1)
        if src.strip().startswith("0x"):
            return "WRITE"
        if dst.strip().startswith("dword ptr [0x"):
            return "READ"
    if mn in ("cmp", "test", "movzx", "movsx", "add", "sub", "or", "and", "xor"):
        return "READ" if mn in ("cmp", "test", "movzx", "movsx") else "RMW"
    if mn == "lea":
        return "LEA(取址)"
    if mn == "push":
        return "PUSH(IMM)"
    return "?"


def show(hit_file, win=24):
    start = max(0, hit_file - win)
    code = d[start:hit_file + win]
    base = VA + start
    print("--- hit file 0x%06X  VA 0x%08X  bytes=%s" % (
        hit_file, VA + hit_file, d[hit_file:hit_file + 4].hex(" ")))
    for ins in md.disasm(code, base):
        mark = ""
        if ins.address <= VA + hit_file < ins.address + ins.size:
            mark = "   <<<< REF"
        print("    0x%08X  %-18s %s %s%s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))


if __name__ == "__main__":
    t = int(sys.argv[1], 16)
    win = 24
    if "--win" in sys.argv:
        win = int(sys.argv[sys.argv.index("--win") + 1], 0)
    hs = hits(t)
    print("target 0x%08X : %d hits" % (t, len(hs)))
    for h in hs:
        show(h, win)
        print()

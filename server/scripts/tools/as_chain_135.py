#!/usr/bin/env python3
"""135 卷工具: 追 AS 注册链的上游 —— 谁调注册器 0x64F620，edi 从哪来。

1) 找所有 `E8 rel32` 指向目标 VA 的调用点
2) 打印调用点前 0x50 字节的反汇编(看 edi/ecx 的建立)
3) 打印调用点后 0x20 字节
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


def cstr(va, maxlen=120):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    if not s or not all(32 <= c < 127 or c in (9, 10) for c in s):
        return None
    return s.decode("latin1")


def dis(va, before, after, title):
    print("=" * 78)
    print(title)
    print("=" * 78)
    start = va - before
    code = d[start - VA:start - VA + before + after]
    for ins in md.disasm(code, start):
        mark = "  <<<" if ins.address == va else ""
        line = "  0x%08X  %-22s %s %s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for tok in ins.op_str.replace(",", " ").split():
            if tok.startswith("0x"):
                try:
                    v = int(tok, 16)
                except ValueError:
                    continue
                s = cstr(v)
                if s:
                    line += "   ; '%s'" % s
        print(line + mark)


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


def main():
    target = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x64F620
    cs = callers(target)
    print("E8 调用点 -> 0x%08X : %d 个" % (target, len(cs)))
    for c in cs:
        print("   0x%08X" % c)
    for c in cs[:3]:
        dis(c, 0x50, 0x20, "caller window @0x%08X" % c)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""改进版提取器：跟进 serialize 内部的 call 到其它写入函数（同模块内）。"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WB, WD = 0xB77B10, 0xB777C0
MAXDEPTH = 3


def bits_of_string_helpers(b, va):
    """0xb759a0=length, 0xc74510=c_str；遇到它们说明是变长串。"""
    return va in (0x0B759A0, 0x0C74510)


def walk(b, va, depth, out, seen):
    if depth > MAXDEPTH or va in seen:
        return
    seen.add(va)
    o = va - BASE
    if not (0 <= o < len(b) - 16):
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    pend = []
    for ins in md.disasm(b[o:o + 0x200], va):
        if ins.id == 0:
            continue
        m, ops = ins.mnemonic, ins.operands
        if m == "push":
            if ops[0].type == 2:
                pend.append(("imm", ops[0].imm))
            elif ops[0].type == 3:
                pend.append(("mem", ins.reg_name(ops[0].mem.base),
                             ops[0].mem.disp))
            else:
                pend.append(("reg", ins.reg_name(ops[0].reg)))
            pend = pend[-6:]
            continue
        if m == "call" and ops[0].type == 2:
            t = ops[0].imm
            if t == WB:
                out.append(("bits", pend[-1] if pend else ("?",)))
            elif t == WD:
                nb = pend[-2] if len(pend) >= 2 else ("?",)
                ptr = pend[-1] if pend else ("?",)
                kind = "data" if nb[0] == "imm" else "var"
                out.append((kind, ptr, nb))
            elif bits_of_string_helpers(b, t):
                out.append(("strhelper", hex(t)))
            elif t in (0x0C427F0,):
                pass
            else:
                # 递归跟进同模块内、且在 0x62xxxx 段的函数
                if 0x625000 <= t < 0x62A000:
                    walk(b, t, depth + 1, out, seen)
            pend = []
            continue
        if m in ("mov", "movzx", "movsx", "lea", "add", "sub", "inc", "dec",
                 "and", "or", "cmp", "test", "xor", "jmp", "je", "jne",
                 "jae", "jb", "jge", "jl", "jle", "jg", "ret"):
            continue


def main():
    va = int(sys.argv[1], 0)
    b = open(DUMP, "rb").read()
    out = []
    walk(b, va, 0, out, set())
    bits = 0
    unknown = False
    for e in out:
        if e[0] == "bits":
            bits += 5
            print("  writeBits(5 位)")
        elif e[0] == "data":
            nb = e[2]
            if nb[0] == "imm":
                bits += nb[1]
                print("  writeData(%s, %d 位)" % (str(e[1]), nb[1]))
            else:
                unknown = True
                print("  writeData(%s, %s) ← 变长" % (str(e[1]), str(nb)))
        elif e[0] == "var":
            unknown = True
            print("  writeData(%s, %s) ← 变长" % (str(e[1]), str(e[2])))
        elif e[0] == "strhelper":
            print("  [字符串辅助 %s]" % e[1])
    print("\n合计 %d 位%s" % (bits, "（含变长，未定）" if unknown else
                              " = %.2f 字节" % (bits / 8.0)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""全量扫描 .text，找出所有 call/jmp 目标以及 call [reg+disp] 形态。"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def secs_of(b):
    e = struct.unpack_from("<I", b, 0x3C)[0]
    n = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I",
                            b, opt + (24 if magic == 0x20B else 28))[0]
    so = opt + osz
    out = []
    for i in range(n):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        out.append((nm, va, vs, rp, rs))
    return ib, out


def main():
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "indirect"
    b = open(path, "rb").read()
    ib, secs = secs_of(b)
    _nm, va, vs, rp, rs = [s for s in secs if s[0] == ".text"][0]
    code = b[rp:rp + rs]
    base = ib + va

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(code, base):
        if ins.id == 0:
            continue
        m = ins.mnemonic
        if m not in ("call", "jmp"):
            continue
        try:
            ops = ins.operands
        except Exception:
            continue
        if not ops:
            continue
        op = ops[0]
        if mode == "indirect" and op.type == 3:  # mem
            print("%#010x  %-6s %s   base=%s disp=%#x" % (
                ins.address, m, ins.op_str,
                ins.reg_name(op.mem.base), op.mem.disp))
        elif mode == "direct" and op.type == 2:  # imm
            print("%#010x  %-6s %#x" % (ins.address, m, op.imm))


if __name__ == "__main__":
    main()

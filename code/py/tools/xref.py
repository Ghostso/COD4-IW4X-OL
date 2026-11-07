#!/usr/bin/env python3
"""全量 PE 交叉引用：查哪些指令引用了某个地址（imm32 或 disp32）。

用途：向上追一个全局/字符串/函数被谁用。
"""
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
    targets = [int(x, 0) for x in sys.argv[2:]]
    b = open(path, "rb").read()
    ib, secs = secs_of(b)
    # 支持非常规节名：取所有可执行的节（IMAGE_SCN_MEM_EXECUTE=0x20000000）
    e = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    so = e + 24 + osz
    execs = []
    for i in range(nsec):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        fl = struct.unpack_from("<I", b, o + 36)[0]
        if fl & 0x20000000 and rs:
            secs.append((nm, va, vs, rp, rs))
    if not secs:
        raise SystemExit("no executable sections")

    hits = {t: [] for t in targets}
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for nm, va, vs, rp, rs in secs:
        if not (fl_ok := True):
            continue
        code = b[rp:rp + rs]
        base_va = ib + va
        for ins in md.disasm(code, base_va):
            if ins.id == 0:
                continue
            try:
                ops = ins.operands
            except Exception:
                continue
            for op in ops:
                v = None
                if op.type == 3 and op.mem.disp:      # X86_OP_MEM
                    v = op.mem.disp
                elif op.type == 2 and op.imm:          # X86_OP_IMM
                    v = op.imm
                if v in hits:
                    hits[v].append((ins.address, "%s [%s] %s" % (
                        ins.mnemonic, nm, ins.op_str)))
    for t in targets:
        print("=== %#x  refs=%d" % (t, len(hits[t])))
        for a, s in hits[t][:40]:
            print("   %#010x  %s" % (a, s))


if __name__ == "__main__":
    main()

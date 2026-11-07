#!/usr/bin/env python3
"""修正版 xref：按节 flags 选可执行节，正确算 ImageBase，同时扫 rel32 与 imm32/disp32。"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def load(path):
    b = open(path, "rb").read()
    e = struct.unpack_from("<I", b, 0x3C)[0]
    n = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I",
                            b, opt + (24 if magic == 0x20B else 28))[0]
    secs = []
    so = opt + osz
    for i in range(n):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1", "replace")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        fl = struct.unpack_from("<I", b, o + 36)[0]
        secs.append((nm, ib + va, vs, rp, rs, fl))
    return b, ib, secs


def main():
    path = sys.argv[1]
    targets = {int(x, 0) for x in sys.argv[2:]}
    b, ib, secs = load(path)
    hits = {t: [] for t in targets}
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for nm, va, vs, rp, rs, fl in secs:
        if not (fl & 0x20000000):
            continue
        code = b[rp:rp + rs]
        for ins in md.disasm(code, va):
            if ins.id == 0:
                continue
            try:
                ops = ins.operands
            except Exception:
                continue
            for op in ops:
                v = None
                if op.type == 3:
                    v = op.mem.disp if op.mem.base == 0 else None
                elif op.type == 2:
                    v = op.imm
                if v is not None and v in targets:
                    hits[v].append((ins.address, nm,
                                    ins.mnemonic + " " + ins.op_str))
    for t in sorted(targets):
        print("=== %#x  refs=%d" % (t, len(hits[t])))
        for a, nm, s in hits[t][:30]:
            print("   %#010x [%s] %s" % (a, nm, s))


if __name__ == "__main__":
    main()

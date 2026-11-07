#!/usr/bin/env python3
"""从内存镜像按 VA 反汇编（off = VA - 0x400000）。"""
import sys

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    va = int(sys.argv[1], 0)
    n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 200
    off = va - BASE
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    shown = 0
    for ins in md.disasm(b[off:off + n], va):
        print("%#010x  %-24s %s %s" % (
            ins.address, " ".join("%02x" % c for c in ins.bytes),
            ins.mnemonic, ins.op_str))
        shown += 1
        if shown > 200:
            break


if __name__ == "__main__":
    main()

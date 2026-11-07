#!/usr/bin/env python3
"""扫描镜像里所有 "push <imm>; ...; call 0xB774E0(读5位并比对)" 的常量，
统计 deserialize 侧期望的标签集合，与 serialize 侧写出的标签集合对照。"""
import collections
import re

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
RB = 0xB774E0   # readBitsExpect(expect)
WB = 0xB77B10   # writeBits(value)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def main():
    b = open(DUMP, "rb").read()
    # 从 0x625000 到 0x62A000 段逐条扫描
    lo, hi = 0x624000 - BASE, 0x62B000 - BASE
    expect = collections.Counter()
    expect_at = collections.defaultdict(list)
    wrote = collections.Counter()
    last_push = None
    for ins in md.disasm(b[lo:hi], 0x624000):
        if ins.mnemonic == "push":
            last_push = (ins.operands[0].imm
                         if ins.operands and ins.operands[0].type == 2
                         else None)
        elif ins.mnemonic == "call" and ins.operands and \
                ins.operands[0].type == 2:
            t = ins.operands[0].imm
            if t in (RB, WB) and last_push is not None:
                (expect if t == RB else wrote)[last_push] += 1
                if t == RB:
                    expect_at[last_push].append(ins.address)
        elif ins.mnemonic in ("mov", "lea"):
            pass  # mov ecx,X 夹在 push 与 call 之间是常态，不打断
        elif ins.mnemonic.startswith("j") or ins.mnemonic.startswith("ret"):
            last_push = None
        else:
            last_push = None
    print("=== deserialize 侧期望标签 (call 0xB774E0) ===")
    for k in sorted(expect):
        print("  0x%02x : %d" % (k, expect[k]))
    print("=== serialize 侧写出标签 (call 0xB77B10) ===")
    for k in sorted(wrote):
        print("  0x%02x : %d" % (k, wrote[k]))
    print("=== 差集 ===")
    print("  只读不写:", [hex(k) for k in expect if k not in wrote])
    print("  只写不读:", [hex(k) for k in wrote if k not in expect])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""确定 0xb7a670 的 this(ecx) 来源，从而算出 [esi+0x4F8] 的绝对地址。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    seg = b[:0x900000]

    # 找所有 call 0xb7a670 的地方，看调用前 ecx 从哪来
    calls = []
    for i in range(len(seg) - 5):
        if seg[i] == 0xE8:
            rel = struct.unpack_from("<i", seg, i + 1)[0]
            if BASE + i + 5 + rel == 0xB7A670:
                calls.append(BASE + i)
    print("call 0xb7a670 共 %d 处" % len(calls))

    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for c in calls[:6]:
        print("\n--- 调用点 %#x 前 12 条 ---" % c)
        o = c - BASE - 80
        for ins in md.disasm(b[o:o + 80], BASE + o):
            print("   %#010x  %s %s" % (ins.address, ins.mnemonic, ins.op_str))


if __name__ == "__main__":
    main()

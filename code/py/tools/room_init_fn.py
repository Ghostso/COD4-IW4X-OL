#!/usr/bin/env python3
"""找包含 0x7e9933 的函数的起点与调用者。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    # 往回找 push ebp; mov ebp,esp
    start = None
    for va in range(0x7e9933, 0x7e0000, -1):
        o = va - BASE
        if b[o:o + 3] == b"\x55\x8b\xec":
            start = va
            break
    print("含 0x7e9933 的函数起点 = %#x" % (start or 0))
    if not start:
        return
    # 打印函数开头
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    o = start - BASE
    print("\n--- 函数开头 40 条 ---")
    n = 0
    for ins in md.disasm(b[o:o + 400], start):
        print("  %#010x  %-20s %s %s" % (ins.address,
              " ".join("%02x" % c for c in ins.bytes),
              ins.mnemonic, ins.op_str))
        n += 1
        if n >= 40:
            break

    # 调用者
    calls = []
    for i in range(len(b) - 5):
        if b[i] == 0xe8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            if BASE + i + 5 + rel == start:
                calls.append(BASE + i)
    print("\n调用者 %d 处: %s" % (len(calls), [hex(x) for x in calls[:12]]))


if __name__ == "__main__":
    main()

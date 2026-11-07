#!/usr/bin/env python3
"""追 0x621740 所在函数的起点、参数来源与调用者。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    start = None
    for va in range(0x621740, 0x620000, -1):
        if b[va - BASE:va - BASE + 3] == b"\x55\x8b\xec":
            start = va
            break
    print("函数起点 = %#x" % (start or 0))

    calls = []
    for i in range(len(b) - 5):
        if b[i] == 0xE8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            if BASE + i + 5 + rel == start:
                calls.append(BASE + i)
    print("调用者 %d 处: %s" % (len(calls), [hex(x) for x in calls[:10]]))

    # imm 引用（可能作为回调注册）
    pat = struct.pack("<I", start)
    imm = []
    k = 0
    while True:
        i = b.find(pat, k)
        if i < 0:
            break
        imm.append(BASE + i)
        k = i + 1
    print("imm 引用 %d 处: %s" % (len(imm), [hex(x) for x in imm[:10]]))


if __name__ == "__main__":
    main()

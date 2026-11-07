#!/usr/bin/env python3
"""找销毁路径（0x63a59a 附近）的函数起点与调用者。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def find_callers(b, target):
    out = []
    for i in range(len(b) - 5):
        if b[i] == 0xe8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            if BASE + i + 5 + rel == target:
                out.append(BASE + i)
    return out


def main():
    b = open(DUMP, "rb").read()
    start = None
    for va in range(0x63a570, 0x638000, -1):
        if b[va - BASE:va - BASE + 3] == b"\x55\x8b\xec":
            start = va
            break
    print("销毁路径所在函数起点 = %#x" % (start or 0))
    if start:
        calls = find_callers(b, start)
        print("调用者 %d 处: %s" % (len(calls), [hex(x) for x in calls[:10]]))
        # 也查 imm 引用（可能被注册为回调）
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

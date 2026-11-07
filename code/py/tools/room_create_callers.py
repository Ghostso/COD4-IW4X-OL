#!/usr/bin/env python3
"""0x639cf5 是"创建房间对象"函数的起点吗？找它的调用者与函数边界。"""
import struct
import sys

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000


def main():
    b = open(DUMP, "rb").read()
    # 找 0x639cf5 之前的函数头
    for va in range(0x639cf5, 0x638000, -1):
        if b[va - BASE:va - BASE + 3] == b"\x55\x8b\xec":
            print("函数起点 = %#x" % va)
            start = va
            break
    # 找调用者
    calls = []
    for i in range(len(b) - 5):
        if b[i] == 0xe8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            if BASE + i + 5 + rel == start:
                calls.append(BASE + i)
    print("调用者 %d 个: %s" % (len(calls), [hex(x) for x in calls[:10]]))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""找 0x639d00 的调用者与注册点。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
TGT = 0x639D00


def main():
    b = open(DUMP, "rb").read()
    calls = []
    for i in range(len(b) - 5):
        if b[i] == 0xe8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            if BASE + i + 5 + rel == TGT:
                calls.append(BASE + i)
    print("call 0x%x : %d 处 %s" % (TGT, len(calls), [hex(x) for x in calls[:10]]))

    # imm 引用（命令注册 handler）
    pat = struct.pack("<I", TGT)
    imm = []
    k = 0
    while True:
        i = b.find(pat, k)
        if i < 0:
            break
        imm.append(BASE + i)
        k = i + 1
    print("imm 引用: %d 处 %s" % (len(imm), [hex(x) for x in imm[:10]]))


if __name__ == "__main__":
    main()

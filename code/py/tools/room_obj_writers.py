#!/usr/bin/env python3
"""找 [0x082e13fc] 的写入点（谁创建房间对象）。
模式：mov dword ptr [0x082e13fc], reg/imm  => A3 xx xx xx xx 或 C7 05 <addr> <imm>
"""
import struct
import sys

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
TARGET = 0x082e13FC


def main():
    b = open(DUMP, "rb").read()
    pat = struct.pack("<I", TARGET)
    print("target VA = %#x" % TARGET)
    print("找写入模式：")

    # A1: mov eax, [target]; A3: mov [target], eax
    a3 = b"\xa3" + pat
    n = b.count(a3)
    print("  A3 (mov [target],eax) : %d" % n)
    k = 0
    while True:
        i = b.find(a3, k)
        if i < 0:
            break
        print("      VA %#x" % (BASE + i))
        k = i + 1

    # C7 05 <target> <imm32>: mov dword [target], imm32
    c7 = b"\xc7\x05" + pat
    n = b.count(c7)
    print("  C7 05 (mov [target],imm32) : %d" % n)
    k = 0
    while True:
        i = b.find(c7, k)
        if i < 0:
            break
        imm = struct.unpack_from("<I", b, i + 6)[0] if i + 10 <= len(b) else 0
        print("      VA %#x  imm=%#x" % (BASE + i, imm))
        k = i + 1

    # 89 0d/15/1d/35/3d <target>: mov [target], ecx/edx/ebx/esi/edi
    for op, reg in ((b"\x89\x0d", "ecx"), (b"\x89\x15", "edx"),
                    (b"\x89\x1d", "ebx"), (b"\x89\x35", "esi"),
                    (b"\x89\x3d", "edi")):
        p = op + pat
        n = b.count(p)
        if n:
            print("  89 %s (mov [target],%s) : %d" %
                  (op[1:].hex(), reg, n))
            k = 0
            while True:
                i = b.find(p, k)
                if i < 0:
                    break
                print("      VA %#x" % (BASE + i))
                k = i + 1


if __name__ == "__main__":
    main()

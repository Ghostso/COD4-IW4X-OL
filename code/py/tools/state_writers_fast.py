#!/usr/bin/env python3
"""快速版：只在代码段范围内找写入点。用 bytes.find 而不是逐字节循环。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
TARGETS = [0x0849ba30, 0x0849ba3d, 0x0849ba50]


def main():
    b = open(DUMP, "rb").read()
    # 只扫前 0x900000（代码 + 常见数据区）
    hi = min(len(b), 0x900000)
    seg = b[:hi]

    for T in TARGETS:
        pat = struct.pack("<I", T)
        print("=" * 56)
        print("target %#x" % T)

        def find_all(p):
            out, k = [], 0
            while True:
                i = seg.find(p, k)
                if i < 0:
                    return out
                out.append(BASE + i)
                k = i + 1

        # 写入：C7 05 <T> <imm32>
        for va in find_all(b"\xc7\x05" + pat):
            off = va - BASE
            imm = struct.unpack_from("<I", seg, off + 6)[0]
            print("   WRITE imm=%#x  @ %#010x" % (imm, va))
        # 写入：A3 <T>  (mov [T],eax)
        for va in find_all(b"\xa3" + pat):
            print("   WRITE eax      @ %#010x" % va)
        # 写入：89 0d/15/1d/35/3d <T>
        for op, reg in ((b"\x89\x0d", "ecx"), (b"\x89\x15", "edx"),
                        (b"\x89\x1d", "ebx"), (b"\x89\x35", "esi"),
                        (b"\x89\x3d", "edi")):
            for va in find_all(op + pat):
                print("   WRITE %-4s    @ %#010x" % (reg, va))
        # 读取/比较计数
        cnt = 0
        for p in (b"\xa1" + pat, b"\x8b\x0d" + pat, b"\x8b\x15" + pat,
                  b"\x83\x3d" + pat, b"\x39\x05" + pat, b"\x3b\x05" + pat):
            k = 0
            while True:
                i = seg.find(p, k)
                if i < 0:
                    break
                cnt += 1
                k = i + 1
        print("   读/比较点: %d" % cnt)


if __name__ == "__main__":
    main()

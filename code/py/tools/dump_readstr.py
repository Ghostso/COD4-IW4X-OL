#!/usr/bin/env python3
"""从内存转储里按 VA 读字符串。需要先确定 dump 偏移 与 VA 的对应关系。"""
import struct
import sys

DUMP = r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin"


def main():
    b = open(DUMP, "rb").read()
    # 校准：已知 'aes' 在 dump 0x9b5ed4，其 VA = 0xdb5ed4
    #   => va_to_off 的基差
    # 用另一处验证: 'common_gametype_mp' dump 0x9b60c8 VA 0xdb60c8
    # 两者差都是 0x400000, 但段内可能有其他映射. 先假设 off = va - 0x400000
    BASE = 0x400000
    print("校准: off = va - %#x (用 aes/IWff 两点验证)" % BASE)
    for va, want in ((0xdb5ed4, b"aes"), (0xdb60c8, b"common_gametype_mp")):
        off = va - BASE
        got = b[off:off + len(want)]
        print("  VA %#x -> off %#x : %r %s" % (va, off, got, "OK" if got == want else "MISMATCH"))

    print()
    for a in sys.argv[1:]:
        va = int(a, 0)
        off = va - BASE
        if not (0 <= off < len(b)):
            print("%#x 越界" % va)
            continue
        z = b.find(b"\x00", off)
        s = b[off:z]
        if all(32 <= c < 127 for c in s) and s:
            print("%#x  %r" % (va, s.decode("ascii")))
        else:
            print("%#x  非文本: %s" % (va, s[:40].hex(" ")))


if __name__ == "__main__":
    main()

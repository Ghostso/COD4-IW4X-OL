#!/usr/bin/env python3
"""追踪：.ff 头里的 8 个 u64 被存到 0x2f79af4 起。
这些是文件的"目录表"。检查 mp_playlists.ff 这 8 个值能否对应到
文件内偏移/长度，从而判断载荷是否未加密、只是"分段"。
"""
import struct
import sys


def main():
    p = sys.argv[1]
    b = open(p, "rb").read()
    print("file=%s size=%d" % (p.rsplit("\\", 1)[-1], len(b)))
    print("head 64:", b[:64].hex(" "))
    print()
    # 头字段：魔数8 + 版本4 + (1+4+4+8) + 8*u64?
    print("按 IWff0100 + ver(4) + 3字段 解析：")
    i = 0
    print("  +0     magic =", b[0:8])
    print("  +8     ver   =", struct.unpack_from("<I", b, 8)[0])
    print("  +12    u32   =", struct.unpack_from("<I", b, 12)[0])
    print("  +16    u32   =", struct.unpack_from("<I", b, 16)[0])
    print("  +20    u64   =", struct.unpack_from("<Q", b, 20)[0])
    print()
    print("从 +28 起当作 8 个 u64：")
    for k in range(8):
        off = 28 + k * 8
        v = struct.unpack_from("<Q", b, off)[0]
        print("  +%3d u64 = %#-18x %d" % (off, v, v))
    print()
    print("从 +12 起当作 8 个 u64：")
    for k in range(8):
        off = 12 + k * 8
        v = struct.unpack_from("<Q", b, off)[0]
        print("  +%3d u64 = %#-18x %d   (<=size: %s)" % (
            off, v, v, v <= len(b)))


if __name__ == "__main__":
    main()

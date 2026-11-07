# -*- coding: utf-8 -*-
"""对比 8/3 上传的裸档案 与 8/1 回的 public.result, 搞清回放格式。

假设: public.result = TLV 外壳 + 裸档案
    0A <owner u64> | 08 04 | 08 01 | 08 01 | 08 <crc> | 13 08 <len> <裸档案>
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "player_profiles", "public.result")
UP = os.path.join(ROOT, "player_profiles", "uploaded_public.bin")


def main():
    pub = open(PUB, "rb").read()
    up = open(UP, "rb").read()
    print("public.result: %d 字节" % len(pub))
    print("uploaded:      %d 字节" % len(up))
    print()
    print("public.result 前 40: %s" % pub[:40].hex(" "))
    print("uploaded   前 16: %s" % up[:16].hex(" "))
    print()
    # 裸档案是否出现在 public.result 里
    i = pub.find(up[:64])
    print("uploaded 前 64 字节在 public.result 里的位置: %s"
          % ("0x%X" % i if i >= 0 else "没找到"))
    # 反过来
    j = up.find(pub[:32])
    print("public 前 32 字节在 uploaded 里的位置: %s"
          % ("0x%X" % j if j >= 0 else "没找到"))
    print()
    # 解析 public.result 的 TLV 头
    print("public.result TLV 解析:")
    k = 0
    while k < min(len(pub), 64):
        t = pub[k]
        if t == 0x0A:
            v = struct.unpack_from("<Q", pub, k + 1)[0]
            print("  0x0A u64 = %d" % v); k += 9
        elif t == 0x08:
            v = struct.unpack_from("<I", pub, k + 1)[0]
            print("  0x08 u32 = %d (0x%X)" % (v, v)); k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            print("  0x13 blob len = %d" % ln)
            blob = pub[k + 6:k + 6 + ln]
            print("       blob 前 16: %s" % blob[:16].hex(" "))
            print("       == uploaded? %s" % (blob == up))
            break
        else:
            print("  ?tag 0x%02X @%d" % (t, k)); break
    return 0


if __name__ == "__main__":
    sys.exit(main())

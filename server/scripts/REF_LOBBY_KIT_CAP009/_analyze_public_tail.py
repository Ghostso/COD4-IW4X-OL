# -*- coding: utf-8 -*-
"""分析 public.result 尾部那 156 个 int32 (tag 0x07)。

它们不在 8/3 上传的裸档案里 -> 是服务端要补的字段。
重点看有没有 == 我们买过的 item(15166/22381/22384)。
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "player_profiles", "public.result")
KNOWN = {15166, 22381, 22384, 29892, 8270, 16339, 18481}


def main():
    pub = open(PUB, "rb").read()
    # 定位 blob 结束
    k = 0
    blob_end = None
    while k < len(pub):
        t = pub[k]
        if t == 0x0A:
            k += 9
        elif t == 0x08:
            k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            blob_end = k + 6 + ln
            break
        else:
            break
    rest = pub[blob_end:]
    print("尾部 %d 字节" % len(rest))
    vals = []
    m = 0
    while m + 5 <= len(rest):
        if rest[m] != 0x07:
            print("  非 0x07 tag @%d: 0x%02X" % (m, rest[m]))
            break
        v = struct.unpack_from("<i", rest, m + 1)[0]
        vals.append(v)
        m += 5
    print("解析出 %d 个 int32" % len(vals))
    print()
    print("全部值:")
    for i, v in enumerate(vals):
        tag = "  <<< 已知 item!" if v in KNOWN else ""
        print("  [%3d] %-10d (0x%X)%s" % (i, v, v & 0xFFFFFFFF, tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""看 80/230(玩家资产 marketplace_player_data) 的结构。"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms

OWNER = 16701785630074219790


def main():
    d = ms.marketplace_player_data(ROOT, OWNER)
    print("marketplace_player_data: %d 字节" % len(d))
    print(d.hex(" "))
    print()
    # 尝试 TLV 解码
    i = 0
    while i < len(d):
        tag = d[i]
        i += 1
        if tag == 0x0A:
            v = struct.unpack_from("<Q", d, i)[0]; i += 8
            print("  u64 %d" % v)
        elif tag == 0x10:
            j = d.find(b"\x00", i)
            print("  str %r" % d[i:j])
            i = j + 1
        elif tag in (0x08, 0x07):
            v = struct.unpack_from("<I", d, i)[0]; i += 4
            print("  u32 %d" % v)
        elif tag == 0x03:
            print("  u8 %d" % d[i]); i += 1
        elif tag == 0x13:
            if i < len(d) and d[i] == 0x08:
                ln = struct.unpack_from("<I", d, i + 1)[0]
                print("  blob %d" % ln)
                i += 5 + ln
            else:
                print("  ?blob"); break
        elif tag == 0x09:
            v = struct.unpack_from("<q", d, i)[0]; i += 8
            print("  i64 %d" % v)
        else:
            print("  ?tag 0x%02X at %d" % (tag, i - 1))
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())

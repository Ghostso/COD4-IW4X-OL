# -*- coding: utf-8 -*-
"""对比我们和 C# 参考实现的 80/203 应答, 逐字节核对。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms

OWNER = 16701785630074219790


def main():
    objs = ms.inventory_results(ROOT, OWNER)
    print("inventory_results: %d 个对象" % len(objs))
    for i, o in enumerate(objs):
        print("  [%d] %d 字节: %s" % (i, len(o), o.hex(" ")))
    print()
    print("marketplace_player_data:")
    d = ms.marketplace_player_data(ROOT, OWNER)
    print("  %d 字节" % len(d))
    print("  前 64: %s" % d[:64].hex(" "))
    print()
    # 逐对象解析, 验证结构
    print("逐对象解析:")
    for i, o in enumerate(objs):
        j = 0
        fields = []
        while j < len(o):
            t = o[j]
            j += 1
            if t == 0x0A:
                v = struct.unpack_from("<Q", o, j)[0]; j += 8
                fields.append("u64=%d" % v)
            elif t == 0x10:
                k = o.find(b"\x00", j)
                fields.append("str=%r" % o[j:k]); j = k + 1
            elif t == 0x08:
                v = struct.unpack_from("<I", o, j)[0]; j += 4
                fields.append("u32=%d" % v)
            elif t == 0x13:
                if o[j] == 0x08:
                    ln = struct.unpack_from("<I", o, j + 1)[0]
                    fields.append("blob=%d" % ln); j += 5 + ln
                else:
                    fields.append("?blob"); break
            elif t == 0x09:
                v = struct.unpack_from("<q", o, j)[0]; j += 8
                fields.append("i64=%d" % v)
            elif t == 0x06:
                v = struct.unpack_from("<H", o, j)[0]; j += 2
                fields.append("u16=%d" % v)
            else:
                fields.append("?tag=0x%02X" % t); break
        print("  [%d] %s" % (i, " ".join(fields)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

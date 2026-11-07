# -*- coding: utf-8 -*-
"""打印那些"Unsupported SKU"失败的购买帧原文 —— 验证解析是否正确。

如果帧结构和成功帧不同, 说明 parse_purchase 取错了字段。
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
BAD = {48, 1981, 1011, 15827, 19621, 31173, 31374, 31819, 41314}


def scan_fields(pl):
    out = []
    i = 0
    n = len(pl)
    while i < n:
        t = pl[i]
        i += 1
        if t in (0x01, 0x03):
            i += 1
        elif t == 0x06:
            i += 2
        elif t in (0x07, 0x08):
            out.append(struct.unpack_from("<I", pl, i)[0]); i += 4
        elif t in (0x09, 0x0A):
            i += 8
        elif t == 0x10:
            j = pl.find(b"\x00", i)
            if j < 0:
                break
            i = j + 1
        elif t == 0x13:
            if i + 5 > n or pl[i] != 0x08:
                break
            ln = struct.unpack_from("<I", pl, i + 1)[0]
            i += 5 + ln
        else:
            break
    return out


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    n = 0
    while off + 6 <= len(raw):
        svc = raw[off]; task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) not in ((80, 154), (93, 131)):
            continue
        vals = scan_fields(pl)
        sku = vals[1] if len(vals) >= 4 else None
        if sku not in BAD:
            continue
        n += 1
        print("=" * 74)
        print("%d/%d len=%d  解析出的 vals=%s" % (svc, task, len(pl), vals))
        print("  hex: %s" % pl.hex())
        # 手工按已知结构解析
        print("  手工:")
        print("    [0:1]=%02X [1:2]=%02X" % (pl[0], pl[1]))
        if len(pl) >= 14:
            print("    u32@8 = %d" % struct.unpack_from("<I", pl, 8)[0])
        if len(pl) >= 54:
            print("    u32@50 = %d (末段 currency?)"
                  % struct.unpack_from("<I", pl, 50)[0])
        if n >= 6:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())

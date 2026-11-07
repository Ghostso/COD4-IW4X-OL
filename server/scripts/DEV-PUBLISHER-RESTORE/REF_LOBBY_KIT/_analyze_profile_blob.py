# -*- coding: utf-8 -*-
"""深入分析 8/3 上传的档案(32768 字节)。

已知: 8/1 返回的 public.result 是 33428 字节(带 TLV 外壳),
      这里解出的是 32768 = 32KB 的裸档案。
目标: 找到名片槽位(cardXxxItemID)的偏移。
"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
OUT = os.path.join(ROOT, "player_profiles", "uploaded_public.bin")


def get_blob():
    raw = open(TASKS, "rb").read()
    off = 0
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) != (8, 3):
            continue
        i = 0
        while i < len(pl):
            if pl[i] == 0x13 and i + 5 <= len(pl) and pl[i + 1] == 0x08:
                blen = struct.unpack_from("<I", pl, i + 2)[0]
                return zlib.decompress(pl[i + 6:i + 6 + blen], 15)
            i += 1
    return None


def main():
    d = get_blob()
    if d is None:
        print("没找到 8/3 档案")
        return 1
    print("档案 %d 字节" % len(d))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(d)
    print("已保存 -> %s" % OUT)
    print()

    # 非零区段
    nz = [(i, d[i]) for i in range(len(d)) if d[i]]
    print("非零字节 %d 个" % len(nz))
    if nz:
        print("首个非零 @0x%X, 最后非零 @0x%X" % (nz[0][0], nz[-1][0]))
    print()
    print("前 64 字节: %s" % d[:64].hex(" "))
    print()
    # 找小整数区(名片槽位可能是小 ID)
    print("前 0x100 的 u32:")
    for o in range(0, min(len(d), 0x100), 4):
        v = struct.unpack_from("<I", d, o)[0]
        if v:
            print("  +0x%03X = %d (0x%X)" % (o, v, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())

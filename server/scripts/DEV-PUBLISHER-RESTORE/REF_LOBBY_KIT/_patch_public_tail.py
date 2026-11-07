# -*- coding: utf-8 -*-
"""实验: 往 public.result 尾部的 125 个 0x07 int32 里填名片 itemID。

假设: 这 125 个槽是"军牌定制可装备清单", 空的槽 = 未解锁。
做法: 保持原结构, 只把指定 itemID 依次塞进为 0 的槽(已存在则跳过)。
可回滚: 备份到 player_profiles/public.result.bak_before_tail_<日期>。

用法:
    python _patch_public_tail.py             # 用内置名单注入
    python _patch_public_tail.py --dump      # 只打印当前尾部
"""
import os
import struct
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "player_profiles", "public.result")

# 用户实际点过 / 交叉验证过的名片类 itemID
ADD_IDS = [22381, 22384, 15166, 29892, 16339, 122, 7110, 29767,
           30059, 30060, 30061, 10001, 10007, 10015, 10028, 10042, 10049]


def split(pub):
    """返回 (头部到 blob 结束的偏移, 尾部 values)。头部 = 0..blob_end。"""
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
            raise ValueError("非预期 tag 0x%02X @%d" % (t, k))
    if blob_end is None:
        raise ValueError("没找到 blob")
    vals = []
    k = blob_end
    while k + 5 <= len(pub) and pub[k] == 0x07:
        vals.append(struct.unpack_from("<i", pub, k + 1)[0])
        k += 5
    return blob_end, vals


def main():
    pub = open(PUB, "rb").read()
    blob_end, vals = split(pub)
    if "--dump" in sys.argv:
        for i, v in enumerate(vals):
            if v:
                print("[%3d] %d" % (i, v))
        return 0
    print("原尾部 %d 槽, 非零 %d 个" % (len(vals), sum(1 for v in vals if v)))
    present = set(vals)
    added = []
    for it in ADD_IDS:
        if it in present:
            continue
        for i, v in enumerate(vals):
            if v == 0:
                vals[i] = it
                present.add(it)
                added.append((i, it))
                break
        else:
            print("  !! 没有空槽, 放弃 %d" % it)
    print("注入 %d 个: %s" % (len(added), added))
    if not added:
        print("无需改动")
        return 0
    bak = PUB + ".bak_before_tail_" + time.strftime("%Y%m%d_%H%M%S")
    with open(bak, "wb") as f:
        f.write(pub)
    print("已备份 ->", bak)
    out = bytearray(pub[:blob_end])
    for v in vals:
        out += bytes([0x07]) + struct.pack("<i", v)
    with open(PUB, "wb") as f:
        f.write(bytes(out))
    print("已写回 %s (%d 字节, 尾部 %d 项)" % (PUB, len(out), len(vals)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

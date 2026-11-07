# -*- coding: utf-8 -*-
"""看 80/230 (marketplace_player_data) 的头部结构, 并统计物品数。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms

OWNER = 16701785630074219790


def main():
    d = ms.marketplace_player_data(ROOT, OWNER)
    print("长度 %d" % len(d))
    print("前 40 字节: %s" % d[:40].hex(" "))
    print()
    # 逐 TLV 走, 找到"物品列表"起点
    i = 0
    # 0x0A u64
    assert d[i] == 0x0A
    owner = struct.unpack_from("<Q", d, i + 1)[0]
    i += 9
    # 0x10 "cod"
    assert d[i] == 0x10
    j = d.find(b"\x00", i + 1)
    tag = d[i + 1:j]
    i = j + 1
    # 0x08 u32 currency? 0x03 u8
    def rd_u32(k):
        assert d[k] == 0x08
        return struct.unpack_from("<I", d, k + 1)[0], k + 5
    def rd_u8(k):
        assert d[k] == 0x03
        return d[k + 1], k + 2
    v1, i = rd_u8(i)
    cp, i = rd_u32(i)
    v2, i = rd_u8(i)
    gp, i = rd_u32(i)
    cnt, i = rd_u32(i)
    print("owner=%d tag=%r" % (owner, tag))
    print("currency1=%d CP=%d currency2=%d GP=%d" % (v1, cp, v2, gp))
    print("★ 头部声明的物品数 = %d, 当前偏移 %d" % (cnt, i))
    # 数一下后面有多少个物品对象 (每个以 0x08 item 开始)
    objs = 0
    k = i
    while k < len(d):
        if d[k] != 0x08:
            break
        objs += 1
        # 跳过整个物品对象: 08 item 08 qty 08 0 13 08 len 08 ffffffff 09 i64 06 u16 08 ffffffff 08 0
        k += 5   # 08 item
        k += 5   # 08 qty
        k += 5   # 08 0
        # 0x13 08 <len>
        if d[k] != 0x13:
            break
        ln = struct.unpack_from("<I", d, k + 2)[0]
        k += 6 + ln
        # 08 ffffffff
        if d[k] != 0x08:
            break
        k += 5
        # 09 i64
        if d[k] != 0x09:
            break
        k += 9
        # 06 u16
        if d[k] != 0x06:
            break
        k += 3
        # 08 ffffffff
        if d[k] != 0x08:
            break
        k += 5
        # 08 0
        if d[k] != 0x08:
            break
        k += 5
    print("实际数出物品数 = %d, 解析结束偏移 %d / %d" % (objs, k, len(d)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

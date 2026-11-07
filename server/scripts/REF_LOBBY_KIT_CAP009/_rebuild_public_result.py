# -*- coding: utf-8 -*-
"""把 8/3 上传的裸档案, 重新包成 8/1 要回的 public.result。

已验证的 public.result 结构:
    0A <owner u64>
    08 <u32 version=4>
    08 <u32 flags=0>
    08 <u32 1>
    08 <u32 crc>           <- == 裸档案前 4 字节(小端读)
    13 08 <u32 len=32768> <裸档案>
    ---- 以下是**装备/拥有清单**(8/3 上传里没有, 必须服务端补) ----
    07 <i32> x125

★ 2026-10-06 实测: 尾部那 125 个 int32 是"可装备清单"。
  前几个: 0, 30060, 30059, 0, 30061, 10007, 10028, 10007, 10049,
          10015, 10042, 10001, 10028, 10001, 10028, 然后 110 个 0。
  其中 10001~10049 那段 + 30059/30060/30061 就是默认名片那套;
  10007 正是原始 7 件小仓库里的第一个 item。

  => 客户端军牌定制里"能换什么", 由这个数组决定。
     我们把 8/3 回空 ACK, 客户端拿不到这份清单 -> 永远只有默认那套。
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROF = os.path.join(ROOT, "player_profiles")
UP = os.path.join(PROF, "uploaded_public.bin")
PUB = os.path.join(PROF, "public.result")

OWNER = 16701785630074219790


def build(raw, owner=OWNER, version=4, flags=0, one=1, tail=None):
    crc = struct.unpack_from("<I", raw, 0)[0]
    out = bytearray()
    out += bytes([0x0A]) + struct.pack("<Q", owner)
    out += bytes([0x08]) + struct.pack("<I", version)
    out += bytes([0x08]) + struct.pack("<I", flags)
    out += bytes([0x08]) + struct.pack("<I", one)
    out += bytes([0x08]) + struct.pack("<I", crc)
    out += bytes([0x13, 0x08]) + struct.pack("<I", len(raw)) + raw
    if tail:
        for v in tail:
            out += bytes([0x07]) + struct.pack("<i", v)
    return bytes(out)


def read_tail(pub_path):
    """从已有 public.result 里读出尾部清单。"""
    pub = open(pub_path, "rb").read()
    k = 0
    while k < len(pub):
        t = pub[k]
        if t == 0x0A:
            k += 9
        elif t == 0x08:
            k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            k += 6 + ln
            break
        else:
            return []
    vals = []
    while k + 5 <= len(pub) and pub[k] == 0x07:
        vals.append(struct.unpack_from("<i", pub, k + 1)[0])
        k += 5
    return vals


def main():
    if not os.path.exists(UP):
        print("缺 %s" % UP)
        return 1
    raw = open(UP, "rb").read()
    print("裸档案 %d 字节, 头4=%s" % (len(raw), raw[:4].hex(" ")))
    packed = build(raw)
    print("打包后 %d 字节 (原 public.result 33428)" % len(packed))
    # 与现有 public.result 逐字节比对(除 blob 内容外)
    if os.path.exists(PUB):
        old = open(PUB, "rb").read()
        print("现有 public.result %d 字节" % len(old))
        same = 0
        for i in range(min(len(old), len(packed))):
            if old[i] != packed[i]:
                break
            same += 1
        print("公共前缀 %d 字节" % same)
        print("  旧头: %s" % old[:34].hex(" "))
        print("  新头: %s" % packed[:34].hex(" "))
    if "--write" in sys.argv:
        # 保留原 public.result 的尾部清单(装备/拥有列表)
        tail = read_tail(PUB)
        print("原尾部清单 %d 项: %s" % (len(tail), tail[:16]))
        packed = build(raw, tail=tail)
        print("带尾部后 %d 字节 (原 33428)" % len(packed))
        open(PUB + ".new", "wb").write(packed)
        print("已写出 %s.new (未覆盖)" % PUB)
    return 0


if __name__ == "__main__":
    sys.exit(main())

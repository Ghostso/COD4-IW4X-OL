# -*- coding: utf-8 -*-
"""解析内存里找到的 SKU 记录结构(客户端自己那份目录)。

来源: REF_LOBBY_KIT\mem_linear\r_259D0000_06400000.bin
  sku=31184 @0x40C8CC / sku=19428 @0x4D762C / sku=37251 @0x424E6C
三条**同一布局**, 步长一致, 后面跟着价格类字段。

目的: 把这条记录的字段布局定下来 —— 有了它, 就能自己造出客户端认的目录,
      也就能回答"为什么军牌定制里看得到、买不了"。
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")

TARGETS = [(31184, 0x40C8CC), (19428, 0x4D762C), (37251, 0x424E6C)]


def dump_record(b, base, before=0x40, after=0x80):
    print("== 记录 @0x%X" % base)
    for off in range(base - before, base + after, 16):
        chunk = b[off:off + 16]
        u32 = struct.unpack("<4I", chunk) if len(chunk) == 16 else ()
        print("  %08X  %-47s  %s"
              % (off, chunk.hex(" "),
                 " ".join("%-10d" % v for v in u32)))


def main():
    if not os.path.exists(SRC):
        print("缺 %s" % SRC)
        return 1
    b = open(SRC, "rb").read()
    for sku, off in TARGETS:
        # 记录起点: 从 sku 往前找到那条记录的头部
        dump_record(b, off)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

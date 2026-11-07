# -*- coding: utf-8 -*-
"""验证假设: 运行时记录 +0x0C = price, +0x14 = item(客户端当前编号)。

方法: 对同时出现在 exe 目录和运行时记录里的 SKU, 直接比较
      +0x14 是否等于 exe.Item, 并统计命中率。
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
CAT = os.path.join(ROOT, "marketplace-catalog.json")
STRIDE = 0x60
NONE = 0xFFFFFFFF


def main():
    cat = {int(e["Id"]): e for e in json.load(open(CAT, "r", encoding="utf-8"))}

    # 收集运行时记录: 优先"第一个"匹配, 但记录每个 sku 的所有候选
    cand = {}
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for off in range(0, len(b) - STRIDE, 4):
            sku = struct.unpack_from("<I", b, off)[0]
            if not (1 <= sku <= 500000):
                continue
            f = [struct.unpack_from("<I", b, off + k)[0] for k in range(0, STRIDE, 4)]
            if f[1] != 0 or f[2] != 0:
                continue
            if f[6] != NONE or f[7] != NONE:
                continue
            if not (1 <= f[3] <= 10000000):
                continue
            cand.setdefault(sku, []).append(f)

    print("运行时记录 sku: %d" % len(cand))
    both = sorted(set(cand) & set(cat))
    print("与 exe 目录重叠: %d" % len(both))

    # 假设: +0x0C=price, +0x14=item
    hit_item = 0
    hit_price = 0
    for s in both:
        # 取任意一条候选
        ok_item = any(f[5] == int(cat[s]["Item"]) for f in cand[s])
        ok_price = any(f[3] == int(cat[s]["Price"]) for f in cand[s])
        hit_item += 1 if ok_item else 0
        hit_price += 1 if ok_price else 0
    print("  某候选满足 +0x0C == exe.Price : %d / %d" % (hit_price, len(both)))
    print("  某候选满足 +0x14 == exe.Item  : %d / %d" % (hit_item, len(both)))

    print()
    print("样本:")
    print("%-8s %-10s %-10s | %-10s %-10s" % ("sku", "mem+0x0C", "mem+0x14", "exe.Price", "exe.Item"))
    for s in both[:35]:
        f = cand[s][0]
        print("%-8d %-10d %-10d | %-10d %-10d" % (s, f[3], f[5], cat[s]["Price"], cat[s]["Item"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

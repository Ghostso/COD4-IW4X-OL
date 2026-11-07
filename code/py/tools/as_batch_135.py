#!/usr/bin/env python3
"""135 卷工具 G: 注册器 -> 分批函数 -> 容器主函数 的三层归属闭合.

1) 载入 828 个注册器 VA (tools/as_regfns_v2.json)
2) 每个注册器找它唯一的 E8 调用者 = 分批函数
3) 分批函数按调用者分组, 每个分批函数再找它的 E8 调用者 = 容器主函数
"""
import json
import struct
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\tools"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def callers_of(target_va):
    pat = b"\xe8"
    out = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        if i + 5 <= N:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if VA + i + 5 + rel == target_va:
                out.append(VA + i)
        i += 1
    return out


def caller_fn(target_va):
    """注册器/分批函数的唯一调用者所在函数 VA(近似: 直接返回调用点所属函数入口)."""
    cs = callers_of(target_va)
    if len(cs) != 1:
        return None, cs
    return cs[0], cs


def entry_of(va):
    f = va - VA
    i = f
    while i > 0:
        if d[i - 1] == 0xCC and d[i - 2] == 0xCC:
            return VA + i
        i -= 1
    return None


if __name__ == "__main__":
    regs = json.load(open(OUT + r"\as_regfns_v2.json"))
    print("注册器 %d 个" % len(regs))
    batch = defaultdict(list)   # 分批函数入口 -> [注册器]
    orphan = []
    for r in regs:
        c, cs = caller_fn(r)
        if c is None:
            orphan.append((r, len(cs)))
            continue
        ent = entry_of(c)
        batch[ent].append(r)
    print("分批函数 %d 个; 非唯一调用者的注册器 %d 个" % (len(batch), len(orphan)))
    if orphan:
        print("  孤儿:", [(hex(a), n) for a, n in orphan])
    tot = sum(len(v) for v in batch.values())
    print("分批函数覆盖注册器 %d / %d" % (tot, len(regs)))
    print()
    print("-- 分批函数(按注册器数排序) --")
    for ent, lst in sorted(batch.items(), key=lambda kv: -len(kv[1])):
        # 分批函数自身的调用者(容器主函数)
        c2, cs2 = caller_fn(ent)
        ent2 = entry_of(c2) if c2 else None
        print("  分批 0x%08X  %3d 个注册器   上层=0x%08X(callsite 0x%08X)" % (
            ent, len(lst), ent2 or 0, c2 or 0))
    print()
    print("-- 上层函数汇总 --")
    up = Counter()
    for ent, lst in batch.items():
        c2, cs2 = caller_fn(ent)
        if c2:
            up[entry_of(c2)] += len(lst)
    for k, v in up.most_common():
        print("  0x%08X  %d" % (k, v))

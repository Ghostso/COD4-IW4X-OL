#!/usr/bin/env python3
"""把手写台账里的 `0x13 0x08 <32位计数> <数据>` 结构识别成
`blob(n) => n*8 位`，从而把"变长"变成"可计算"。

判据（来自 0x625be0 StartGame::serialize 与 0x4f3eb0 读侧）：
  写侧: writeBits(0x13); writeBits(0x08); writeData(&n, 32);
        writeData(ptr, n*8)         ← 长度 = 计数字段 × 8
  读侧: readBitsExpect(0x13); readBitsExpect(0x08);
        readData(&n, 32); readData(buf, min(cap,n)*8)

用法: python -I tools/blob_fold.py
输出：每个 serialize 的 fold 后表达式。
"""
import re
import subprocess
import sys

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402


def fold(seq):
    """把 (tag,data) 序列折叠成可读表达式。返回 (text, unknown_flag)。"""
    items = []
    i = 0
    n = len(seq)
    unknown = False
    while i < n:
        lp, kind, w, at, v = seq[i]
        if kind == "call":
            items.append(("call", v))
            i += 1
            continue
        if kind != "tag":
            i += 1
            continue
        # 看是不是 blob 起始：tag 0x13
        if v == 0x13 and i + 3 < n:
            _, k2, _, _, v2 = seq[i + 1]
            _, k3, w3, _, _ = seq[i + 2]
            _, k4, w4, _, _ = seq[i + 3]
            if k2 == "tag" and v2 == 0x08 and k3 == "data" and w3 == 32:
                items.append(("blob", i, w4))
                i += 4
                continue
        # 普通 tag + data
        if i + 1 < n and seq[i + 1][1] == "data":
            w1 = seq[i + 1][2]
            items.append(("field", v, w1, lp))
            i += 2
        else:
            items.append(("tagonly", v))
            i += 1
    return items, unknown


def render(items):
    out = []
    for it in items:
        if it[0] == "call":
            out.append("[%s]" % it[1])
        elif it[0] == "field":
            _, tag, w, lp = it
            out.append(("%s0x%02x:%s" % ("L" if lp else "", tag,
                                         w if w else "VAR")))
        elif it[0] == "blob":
            _, idx, w4 = it
            if isinstance(w4, int):
                out.append("blob(%d B)" % (w4 // 8))
            else:
                out.append("blob(u32 n => n*8)")
        elif it[0] == "tagonly":
            out.append("0x%02x:?" % it[1])
    return " ".join(out)


def main():
    b = open(E.DUMP, "rb").read()
    rows = E.rows_from_vtable()
    seen = set()
    for name, sva, dva in rows:
        for label, va, tc, dc in (("ser", sva, E.WB, E.WD),
                                  ("der", dva, E.RB, E.RD)):
            iv = int(va, 16)
            if (iv, tc) in seen:
                continue
            seen.add((iv, tc))
            seq, loops = E.analyze(b, iv, tc, dc)
            if not seq:
                continue
            items, _ = fold(seq)
            pre_bits = 0
            loop_bits = 0
            for it in items:
                if it[0] == "field":
                    w = it[2]
                    if isinstance(w, int):
                        if it[3]:
                            loop_bits += 5 + w
                        else:
                            pre_bits += 5 + w
                elif it[0] == "blob":
                    w4 = it[2]
                    if isinstance(w4, int):
                        pre_bits += 47 + w4
                    else:
                        pre_bits += 47
            print("%-44s %s  pre=%-5d loop=%-5d x%d" % (
                name, label, pre_bits, loop_bits, loops))
            print("      " + render(items))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""把每个 0x00 字节按"它在文法里的角色"分类，而不是笼统计数。

角色分类（互斥）：
  T  终止符：payload 最后一个字节，或 tag=0x00 的独立元素
  S  字符串 NUL：位于 0x10 后、字符串内容结尾的那个 0x00
  F  定长字段内部：0x01/0x03/0x06/0x07/0x08/0x09/0x0a 的载荷字节里
  B  blob/数组载荷内部：0x13 / 0x6b / 0x6c 的数据区
  X  未归类（语法失败的残留）

用法: python -I tools/zero_role_census.py corpus out
"""
import collections
import json
import struct
import sys

FIXED = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0A: 8}


class Buf:
    def __init__(self, b):
        self.b, self.i, self.ok = b, 0, True


def parse(b):
    """返回 [(role, start, end)] 覆盖全部字节；失败则剩余全记 X。"""
    n = len(b)
    out = []
    i = 0

    def take(k):
        nonlocal i
        if i + k > n:
            return None
        v = b[i:i + k]
        i += k
        return v

    while i < n:
        t = take(1)
        if t is None:
            break
        t = t[0]
        if t == 0x00:
            out.append(("T", i - 1, i))
            continue
        if t in FIXED:
            v = take(FIXED[t])
            if v is None:
                out.append(("X", i - 1, n))
                return out
            out.append(("F", i - 1 - 0, i) if False else ("F", i - 1, i))
            continue
        if t == 0x10:
            z = b.find(b"\x00", i)
            if z < 0:
                out.append(("X", i - 1, n))
                return out
            i = z + 1
            out.append(("S", z, i))
            continue
        if t == 0x13:
            if i + 1 <= n and b[i] == 0x08:
                i += 1
                if i + 4 <= n:
                    ln = struct.unpack("<I", b[i:i + 4])[0]
                    i += 4
                    if i + ln <= n:
                        i += ln
                        out.append(("B", i - ln, i))
                        continue
            out.append(("X", i - 1, n))
            return out
        if t in (0x6B, 0x6C):
            if i + 1 <= n and b[i] == 0x08:
                i += 1
                if i + 4 <= n:
                    blen = struct.unpack("<I", b[i:i + 4])[0]
                    i += 4
                    if i + 4 <= n:
                        i += 4
                        if i + blen <= n:
                            i += blen
                            out.append(("B", i - blen, i))
                            continue
            out.append(("X", i - 1, n))
            return out
        # 未知标签：本字节记 X，停止（避免无限循环）
        out.append(("X", i - 1, i))
        return out
    return out


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    out = open(sys.argv[2], "w", encoding="utf-8")

    def w(s=""):
        print(s)
        out.write(s + "\n")

    role_cnt = collections.Counter()
    zero_by_role = collections.Counter()
    faults = 0
    per_task = collections.defaultdict(collections.Counter)
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        segs = parse(b)
        covered = set()
        for role, s, e in segs:
            for k in range(s, e):
                covered.add(k)
                role_cnt[role] += 1
                if b[k] == 0x00:
                    zero_by_role[role] += 1
                    per_task[(r["svc"], r["task"])][role] += 1
        if len(covered) < len(b):
            faults += 1
            for k in range(len(b)):
                if k not in covered and b[k] == 0:
                    zero_by_role["X"] += 1

    total_zero = sum(zero_by_role.values())
    w("=== 0x00 按角色分类（corpus=%d）===" % len(corpus))
    w("解析未覆盖的 payload: %d" % faults)
    w("")
    w("%-4s %-14s %-10s %s" % ("角色", "含义", "0 字节数", "占比"))
    names = {"T": "终止符", "S": "字符串 NUL", "F": "整型字段内",
             "B": "blob/数组内", "X": "未归类"}
    for role in ("T", "S", "F", "B", "X"):
        z = zero_by_role[role]
        w("%-4s %-14s %-10d %.2f%%" % (
            role, names[role], z, 100.0 * z / total_zero if total_zero else 0))
    w("%-4s %-14s %-10d" % ("合计", "", total_zero))
    w("")
    w("=== 各角色覆盖的字节数（含非零）===")
    for role in ("T", "S", "F", "B", "X"):
        w("  %s: %d" % (role, role_cnt[role]))
    w("")
    w("=== 每个 task 的零分布（前 20）===")
    for k, c in sorted(per_task.items(),
                       key=lambda kv: -sum(kv[1].values()))[:20]:
        w("  %d/%-4d T=%-5d S=%-5d F=%-6d B=%-6d" % (
            k[0], k[1], c["T"], c["S"], c["F"], c["B"]))
    out.close()


if __name__ == "__main__":
    main()

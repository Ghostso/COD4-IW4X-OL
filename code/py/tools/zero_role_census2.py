#!/usr/bin/env python3
"""用官方文法 v5 的 parse（6848/6848）拿到元素列表，
再按元素边界给每个 0x00 打角色标签。

角色：
  T  终止符（payload 尾部那串 0x00）
  S  字符串内容的 NUL 结尾（0x10 元素的值）
  F  定长整型字段的载荷字节（0x01/03/06/07/08/09/0a）
  B  blob/数组载荷字节（0x13/6b/6c）
  H  标签字节本身（不可能是 0x00）
  L  子结构标记（0x13/6b/6c 的 0x08、长度前缀 u32、计数 u32）
"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

FIXED = G.FIXED


def walk(buf, b, roles):
    """递归遍历，标记每个字节的角色。buf.i 为当前位置。"""
    while buf.i < len(b):
        start = buf.i
        if b[buf.i] == 0x00:
            while buf.i < len(b) and b[buf.i] == 0x00:
                roles[buf.i] = "T"
                buf.i += 1
            return
        t = b[buf.i]
        if t in FIXED:
            for k in range(start, start + 1 + FIXED[t]):
                roles[k] = "F"
            buf.i = start + 1 + FIXED[t]
            continue
        if t == 0x10:
            z = b.find(b"\x00", start + 1)
            if z < 0:
                return
            for k in range(start + 1, z):
                roles[k] = "S"
            roles[z] = "S"
            buf.i = z + 1
            continue
        if t in (0x13, 0x6B, 0x6C):
            # 13 08 <u32 len> <len>      /  6b|6c 08 <u32 blen> <blen> <u32 cnt>
            roles[start] = "L"
            roles[start + 1] = "L"
            ln = int.from_bytes(b[start + 2:start + 6], "little")
            for k in range(start + 2, start + 6):
                roles[k] = "L"
            body_s = start + 6
            for k in range(body_s, body_s + ln):
                roles[k] = "B"
            end = body_s + ln
            if t in (0x6B, 0x6C):
                for k in range(end, end + 4):
                    roles[k] = "L"
                end += 4
            buf.i = end
            continue
        return  # 未知标签，停


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    out = open(sys.argv[2], "w", encoding="utf-8")

    def w(s=""):
        print(s)
        out.write(s + "\n")

    zc = collections.Counter()
    bc = collections.Counter()
    bad = 0
    per_task = collections.defaultdict(collections.Counter)
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        good, _elems, why = G.parse(b)
        if not good:
            bad += 1
            continue
        roles = {}
        walk(G.Buf(b), b, roles)
        for i, x in enumerate(b):
            role = roles.get(i, "?")
            bc[role] += 1
            if x == 0:
                zc[role] += 1
                per_task[(r["svc"], r["task"])][role] += 1

    names = {"T": "终止符", "S": "字符串 NUL", "F": "整型字段载荷",
             "B": "blob/数组载荷", "L": "长度/标记字节", "?": "未标注"}
    tot = sum(zc.values())
    w("=== 0x00 角色分类（corpus=%d, 解析失败=%d）===" % (len(corpus), bad))
    w("%-3s %-16s %-9s %-8s %s" % ("角色", "含义", "零字节数", "占比", "字节覆盖"))
    for role in ("T", "S", "F", "B", "L", "?"):
        if zc[role] == 0 and bc[role] == 0:
            continue
        w("%-3s %-16s %-9d %-8s %d" % (
            role, names[role], zc[role],
            "%.2f%%" % (100.0 * zc[role] / tot) if tot else "-", bc[role]))
    w("%-3s %-16s %-9d" % ("", "合计", tot))
    w("")
    w("=== 每个 task 的零角色分布（前 24）===")
    for k, c in sorted(per_task.items(),
                       key=lambda kv: -sum(kv[1].values()))[:24]:
        w("  %3d/%-4d T=%-5d S=%-5d F=%-6d B=%-7d L=%-5d" % (
            k[0], k[1], c["T"], c["S"], c["F"], c["B"], c["L"]))
    out.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""字节 0x70 的全语料角色分账 + 语境分析。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    role = collections.Counter()
    per_task = collections.Counter()
    blob_text = 0
    blob_bin = 0
    blob_ctx = collections.Counter()
    field_vals = collections.Counter()
    str_words = collections.Counter()
    total = 0
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        roles = {}
        Z.walk(G.Buf(b), b, roles)
        for i, x in enumerate(b):
            if x != 0x70:
                continue
            total += 1
            ro = roles.get(i, "?")
            role[ro] += 1
            per_task[(r["svc"], r["task"], ro)] += 1
        # blob 内部分型
        for t, v in els:
            if t == 0x13 and isinstance(v, bytes) and 0x70 in v:
                c = v.count(0x70)
                pr = sum(1 for x in v if 0x20 <= x <= 0x7e or x in (9, 10, 13))
                if len(v) and pr / len(v) > 0.6:
                    blob_text += c
                else:
                    blob_bin += c
                    for i, x in enumerate(v):
                        if x == 0x70:
                            blob_ctx[v[i - 1] if i > 0 else -1] += 1
            if t == 0x10 and isinstance(v, bytes) and b"p" in v:
                for w in v.decode("latin1").split():
                    if "p" in w.lower():
                        str_words[w.strip(";,")] += 1
        # 整型字段值 == 0x70
        for t, v in els:
            if t in G.FIXED and isinstance(v, bytes) and len(v) == G.FIXED[t]:
                iv = int.from_bytes(v, "little", signed=(t == 0x07))
                if iv == 0x70:
                    field_vals[hex(t)] += 1

    print("=== 0x70 总量 %d ===" % total)
    names = {"S": "字符串内容(字母 p)", "B": "blob 载荷",
             "F": "整型字段载荷", "L": "长度/标记", "T": "终止符",
             "?": "未标注"}
    for k in ("S", "B", "F", "L", "T", "?"):
        if role[k]:
            print("  %-2s %-22s %d (%.1f%%)" % (
                k, names[k], role[k], 100.0 * role[k] / total))
    print()
    print("=== 按 task × 角色 ===")
    for k, v in per_task.most_common(14):
        print("  %3d/%-4d role=%s : %d" % (k[0], k[1], k[2], v))
    print()
    print("=== blob 内型 ===")
    print("  文本型 blob 里的 0x70: %d" % blob_text)
    print("  二进制型 blob 里的 0x70: %d" % blob_bin)
    print("  二进制 blob 里 0x70 的前一字节 top8:")
    for k, v in blob_ctx.most_common(8):
        print("    %-6s : %d" % (("START" if k < 0 else "%02x" % k), v))
    print()
    print("=== 整型字段值恰为 0x70 的 ===")
    print("  " + (str(dict(field_vals)) if field_vals else "NONE"))
    print()
    print("=== 含 'p' 的词 top12 ===")
    for w, c in str_words.most_common(12):
        print("  x%-5d %s" % (c, w))


if __name__ == "__main__":
    main()

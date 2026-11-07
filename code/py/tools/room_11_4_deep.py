#!/usr/bin/env python3
"""11/4 内层结构深度解析。

已观察到的内层开头：
    <u32 内容长度>
    02 <m> 00 00            ← m = 2/4/6/8/0x0d  疑为"字段组数"
    <若干 u32>
    ...

本脚本按假设的语法逐字段解析，并验证长度闭环。
"""
import json
import struct
import sys
from collections import Counter

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse


def analyze(body):
    """返回 [(off, kind, value, raw_hex)]"""
    out = []
    n = len(body)
    i = 0
    # 首 4 字节 = 内容长度
    if n < 4:
        return None
    declared = struct.unpack_from("<I", body, 0)[0]
    out.append((0, "len", declared, body[0:4].hex(" ")))
    i = 4
    # 之后：02 <m> 00 00
    if i + 4 <= n:
        out.append((i, "hdr", "%02x %d 00 00" % (body[i], body[i + 1]),
                    body[i:i + 4].hex(" ")))
        i += 4
    # 剩余按 u32 读
    while i + 4 <= n:
        v = struct.unpack_from("<I", body, i)[0]
        out.append((i, "u32", v, body[i:i + 4].hex(" ")))
        i += 4
    if i < n:
        out.append((i, "tail", body[i:].hex(" "), body[i:].hex(" ")))
    return out


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rs = [r for r in corpus if (r["svc"], r["task"]) == (11, 4)]
    print("11/4 samples=%d" % len(rs))
    forms = Counter()
    for r in rs:
        p = bytes.fromhex(r["payload"])
        ok, elems, _ = parse(p)
        if not ok:
            continue
        blob = None
        for k, v in elems:
            if k == 0x13:
                blob = v
                break
        if blob:
            forms[blob] += 1

    print("distinct blobs: %d" % len(forms))
    # 按内部 hdr 分组
    hdr_groups = Counter()
    for b, n in forms.items():
        if len(b) >= 8:
            hdr_groups[(b[4], b[5], b[6], b[7])] += n
    print("\n内部 hdr 分布（blob[4:8]）：")
    for k, n in hdr_groups.most_common():
        print("  %s  x%d" % (k, n))

    print("\n=== 每种 hdr 的最常见样本逐 u32 ===")
    seen = set()
    for b, n in forms.most_common(200):
        if len(b) < 8:
            continue
        key = (b[4], b[5], b[6], b[7])
        if key in seen:
            continue
        seen.add(key)
        print("\n--- hdr=%s  blob_len=%d  x%d" % (key, len(b), n))
        res = analyze(b)
        if res is None:
            continue
        for off, kind, val, raw in res[:26]:
            print("   %+04d %-5s %-14s %s" % (off, kind, str(val), raw))
        if len(res) > 26:
            print("   ... 还有 %d 个字段" % (len(res) - 26))


if __name__ == "__main__":
    main()

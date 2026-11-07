#!/usr/bin/env python3
"""用 v5 解析器正确提取 0x6b / 0x6c 数组的 (字节长, 元素数) 对。"""
import json
import sys
from collections import Counter

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse  # noqa: E402


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rows = {}
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        ok, elems, why = parse(b)
        if not ok:
            print("PARSE FAIL", r["svc"], r["task"], why)
            continue
        key = (r["svc"], r["task"])
        for t, v in elems:
            if t in (0x6B, 0x6C):
                cnt, body = v
                bl = len(body)
                sig = (t, bl, cnt, (bl // cnt) if cnt else None,
                       body[:12].hex())
                rows.setdefault(key, Counter())[sig] += 1

    for key in sorted(rows):
        print("=== %d/%d" % key)
        for (t, bl, cnt, w, head), n in rows[key].most_common(10):
            print("   tag%02x  bytes=%-6d count=%-5d width=%-4s head=%-26s  x%d"
                  % (t, bl, cnt, w, head, n))


if __name__ == "__main__":
    main()

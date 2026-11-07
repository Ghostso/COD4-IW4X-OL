#!/usr/bin/env python3
"""mmstart 字段切分（纯 ASCII 输出）。"""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rs = [r for r in corpus if (r["svc"], r["task"]) == (6, 14)]
    bodies = Counter()
    for r in rs:
        p = bytes.fromhex(r["payload"])
        ok, elems, _ = parse(p)
        if not ok:
            continue
        u64 = None
        for k, v in elems:
            if k == 0x0A:
                u64 = v
            elif k == 0x13:
                bodies[(u64, v)] += 1

    keys = defaultdict(Counter)
    for (u, b), n in bodies.items():
        # blob 内层：u32 长度 + 文本
        if len(b) < 5:
            continue
        txt = b[4:].decode("latin1", "replace")
        if not txt.startswith("mmstart"):
            continue
        for part in txt.split(";"):
            part = part.strip()
            if not part:
                continue
            k = part.split()[0]
            keys[k][part] += n

    print("mmstart field keys: %s" % sorted(keys))
    for k in sorted(keys):
        vals = keys[k]
        tot = sum(vals.values())
        print("\n--- key '%s'  (total %d, distinct %d)" % (k, tot, len(vals)))
        for full, n in vals.most_common(10):
            safe = full.encode("ascii", "replace").decode("ascii")
            print("    x%-4d %s" % (n, safe[:110]))


if __name__ == "__main__":
    main()

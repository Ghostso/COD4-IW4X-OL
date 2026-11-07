#!/usr/bin/env python3
"""从 corpus.json 里逐 (svc,task) 打印样本, 供反推线格式文法。"""
import json
import sys
from collections import defaultdict


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    want = sys.argv[2] if len(sys.argv) > 2 else None
    per = defaultdict(list)
    for r in corpus:
        per[(r["svc"], r["task"])].append(r)
    for k in sorted(per):
        if want and want != "%d/%d" % k:
            continue
        rs = per[k]
        seen = []
        for r in rs:
            if r["payload"] not in [s["payload"] for s in seen]:
                seen.append(r)
            if len(seen) >= 3:
                break
        print("=== %d/%d  count=%d distinct=%d" % (k[0], k[1], len(rs),
              len({x["payload"] for x in rs})))
        for r in seen:
            p = bytes.fromhex(r["payload"])
            print("  len=%d run=%s" % (len(p), r["run"]))
            for off in range(0, min(len(p), 192), 16):
                chunk = p[off:off + 16]
                hexs = " ".join("%02x" % c for c in chunk)
                asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
                print("    %04x  %-47s  %s" % (off, hexs, asc))
        print()


if __name__ == "__main__":
    main()

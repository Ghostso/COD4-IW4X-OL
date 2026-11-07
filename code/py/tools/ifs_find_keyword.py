#!/usr/bin/env python3
"""在所有 .ifs 的明文清单区里找特定关键词（菜单/UI/脚本）。"""
import os
import re
import sys


def main():
    root = sys.argv[1]
    kws = sys.argv[2:] or ["menu", "ui_mp", "codescripts", "gsc", "playlist"]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    hits = {k: [] for k in kws}
    for fn in files:
        p = os.path.join(root, fn)
        with open(p, "rb") as f:
            w = f.read(512 * 1024)
        for k in kws:
            for m in re.finditer(rb"[ -~]*" + k.encode() + rb"[ -~]*", w,
                                 re.IGNORECASE):
                s = m.group().decode("latin1")
                if len(s) < 8:
                    continue
                hits[k].append((fn, s))
    for k in kws:
        hs = hits[k]
        seen = set()
        uniq = []
        for fn, s in hs:
            key = s.strip("\x00")
            if key in seen:
                continue
            seen.add(key)
            uniq.append((fn, s))
        print("=== %r  %d 条唯一 ===" % (k, len(uniq)))
        for fn, s in uniq[:12]:
            print("   %-50s %r" % (fn[:50], s[:100]))
        print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate SHA256SUMS.txt for every deliverable in this directory.
Run:  python -I make_sums.py
"""
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXCLUDE = {"SHA256SUMS.txt"}
EXCLUDE_DIRS = {"_work", "__pycache__"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    lines = []
    for name in sorted(os.listdir(HERE)):
        p = os.path.join(HERE, name)
        if not os.path.isfile(p) or name in EXCLUDE:
            continue
        if not (name.endswith(".md") or name.endswith(".json") or
                name.endswith(".csv") or name.endswith(".py") or name.endswith(".txt")):
            continue
        lines.append("%s  %s" % (sha256(p), name))
    with open(os.path.join(HERE, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %d entries" % len(lines))


if __name__ == "__main__":
    main()

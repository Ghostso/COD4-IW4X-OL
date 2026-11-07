#!/usr/bin/env python3
"""137 卷工具: 在镜像里搜 ASCII/UTF-16 串, 打印 VA + 前后上下文。
用法: python -I tools/s137_strfind.py <str> [--ctx N] [--wide]
"""
import struct
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    ctx = 0
    for f in flags:
        if f.startswith("--ctx"):
            ctx = int(f.split("=")[1]) if "=" in f else 16
    s = args[0].encode("latin1")
    wide = "--wide" in flags
    pats = [s]
    if wide:
        pats = [s.decode().encode("utf-16-le")]
    pat = pats[0]
    pos = 0
    hits = []
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        va = VA + i
        before = d[max(0, i - ctx):i]
        after = d[i + len(pat):i + len(pat) + ctx]
        hits.append((va, before, after))
    print("'%s'%s : %d hits" % (args[0], " (wide)" if wide else "", len(hits)))
    for va, b, a in hits:
        print("  0x%08X  ...%r[%s]%r..." % (
            va, b, args[0], a))


if __name__ == "__main__":
    main()

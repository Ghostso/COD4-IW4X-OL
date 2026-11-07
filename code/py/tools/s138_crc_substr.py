#!/usr/bin/env python3
"""s138_crc_substr: 在 playlist 明文与镜像的 ASCII 串上, 对**所有子串**(<=48B)算 crc32,
找 A(0xD692ADAB)/OLD(0xD6F01F9B)。用于判定 A 是否是某个字符串的 crc32。
"""
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = 0xD692ADAB
O = 0xD6F01F9B
T = {A: "A", O: "OLD"}

MAXL = 48
hits = []


def scan(buf, label):
    n = len(buf)
    for i in range(n):
        if not (32 <= buf[i] < 127):
            continue
        for L in range(1, MAXL + 1):
            if i + L > n:
                break
            seg = buf[i:i + L]
            if seg[-1] < 32 or seg[-1] >= 127:
                break
            c = zlib.crc32(seg) & 0xffffffff
            if c in T:
                hits.append((T[c], label, i, seg))
                print("HIT %s %s @%d %r" % (T[c], label, i, seg))


P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"
pl = open(P, "rb").read()
scan(pl, "playlist")
print("playlist done, hits=%d" % len(hits))

# image strings only (join printable runs)
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read()
# sample: restrict to ASCII-heavy .rdata region and string-ish areas to keep runtime sane
for m in re.finditer(rb"[ -~]{6,120}", d):
    s = m.group()
    n = len(s)
    for i in range(n):
        for L in range(1, MAXL + 1):
            if i + L > n:
                break
            c = zlib.crc32(s[i:i + L]) & 0xffffffff
            if c in T:
                hits.append((T[c], "image", m.start() + i, s[i:i + L]))
                print("HIT %s image @0x%X %r" % (T[c], m.start() + i, s[i:i + L]))
print("total hits=%d" % len(hits))

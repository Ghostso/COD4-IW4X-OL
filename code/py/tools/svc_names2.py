#!/usr/bin/env python3
"""全面搜服务名: ASCII 大小写 / UTF-16LE / 前缀子串, 并打印上下文。"""
import struct
import sys

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
BASE = 0x400000

names = ["leaderboard", "matchmaking", "marketplace", "presence", "messaging",
         "stats", "reward", "friends", "notification", "session", "lobby",
         "party", "room", "clan", "storage", "achievement", "title", "userstorage"]

def find_all(hay, needle):
    out = []
    i = 0
    while True:
        p = hay.find(needle, i)
        if p < 0:
            return out
        out.append(p)
        i = p + 1

print("=== ASCII (大小写混合搜索) ===")
for n in names:
    for variant in (n.encode(), n.upper().encode(), n.capitalize().encode()):
        offs = find_all(data, variant)
        if offs:
            print("  %-16s %-18s n=%d  %s" % (n, variant.decode(), len(offs),
                  ["0x%X" % o for o in offs[:8]]))
            break
    else:
        print("  %-16s (none)" % n)

print("\n=== UTF-16LE ===")
for n in names:
    variant = n.encode("utf-16-le")
    offs = find_all(data, variant)
    if offs:
        print("  %-16s n=%d  %s" % (n, len(offs), ["0x%X" % o for o in offs[:8]]))

print("\n=== 上下文: 每个 ASCII 命中前后 48 字节的可打印串 ===")
for n in names:
    for variant in (n.encode(), n.upper().encode(), n.capitalize().encode()):
        offs = find_all(data, variant)
        if offs:
            for o in offs[:4]:
                lo = max(0, o - 48)
                hi = min(len(data), o + 48)
                chunk = data[lo:hi]
                printable = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                print("  [%s @0x%X] %s" % (n, o, printable))
            break

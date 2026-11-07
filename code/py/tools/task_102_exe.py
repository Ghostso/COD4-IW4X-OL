#!/usr/bin/env python3
"""在客户端 EXE 与 lobby_server.py 里搜 102 服务的线索。
102 服务的 tag 是 0x66。查 EXE 里是否有 "dw" 或服务名。"""
import re

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()

# 搜索可能的服务名（Demonware 服务名常见: matchmaking, marketplace, userstorage, ...）
cands = [b"userstorage", b"UserStorage", b"user_storage", b"storage",
         b"cdkey", b"entitlement", b"leaderboard", b"stats", b"richpresence",
         b"Presence", b"notification", b"Achievement", b"achievement"]
for c in cands:
    n = data.count(c)
    if n:
        print("%-20s x%d" % (c.decode("latin1", "replace"), n))

# 搜 0x66 服务可能对应的明文名（如果有）
print("\n=== 搜 'dw' 前缀服务名 ===")
for m in re.finditer(rb"dw[A-Za-z]{4,24}", data):
    s = m.group()
    print("  %s @0x%X" % (s.decode("latin1", "replace"), m.start()))
    if m.start() > 0x7A0000:
        break

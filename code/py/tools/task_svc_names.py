#!/usr/bin/env python3
"""找 Demonware 服务号表：EXE 里服务名附近的整数常量，或已知的 service->name 映射。
已知: 6=instant message, 8=userstorage/profile, 10=publisher file, 11=room,
21=matchmaking, 28=task, 71=telemetry, 80=marketplace, 93=wallet2, 4=stats,
3=?, 9=?, 12=?, 29=?, 68=?, 102=?
搜 EXE 里 102 附近的字符串表。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()

# 常见 Demonware 服务名 -> 服务号（从公开 DW 文档/COD 系列）
# 在 EXE 里搜 "UserStorage" "Matchmaking" 等大写
names = [b"Matchmaking", b"Marketplace", b"UserStorage", b"Leaderboard",
         b"Achievements", b"Presence", b"Messaging", b"Task", b"Stats",
         b"Reward", b"Friends", b"Notification", b"Telemetry", b"Title",
         b"Session", b"Lobby", b"Party", b"Room", b"Clan"]
print("=== 服务名在 EXE 出现次数 ===")
for n in names:
    c = data.count(n)
    if c:
        print("  %-16s x%d" % (n.decode(), c))

# 搜小写版本
print("\n=== 小写服务名 ===")
for n in [b"matchmaking", b"marketplace", b"userstorage", b"leaderboard",
          b"achievements", b"presence", b"messaging"]:
    c = data.count(n)
    if c:
        print("  %-16s x%d" % (n.decode(), c))

# 102 服务的 tag 是 0x66='f'. 但服务号是协议里的整数。
# 看看是否有 "Service" 字符串表
print("\n=== 含 'Service' 的串 ===")
import re
cnt = 0
for m in re.finditer(rb"[A-Za-z]{3,30}Service", data):
    s = m.group().decode("latin1", "replace")
    print("  %s" % s)
    cnt += 1
    if cnt > 60:
        break

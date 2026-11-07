#!/usr/bin/env python3
"""在客户端 EXE 里找 Demonware 服务号 -> 服务名的映射表。
策略: 找 "Leaderboard"/"Matchmaking" 等名称串的指针表, 或紧邻的 u32 服务号。
也搜 service 号 102(0x66)、21(0x15)、80(0x50)、93(0x5d) 附近的字符串引用。"""
import re
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
BASE = 0x400000

# 1) 找所有服务名字符串的偏移
names = [b"Matchmaking", b"Marketplace", b"Leaderboard", b"Presence", b"Messaging",
         b"Task", b"Stats", b"Reward", b"Friends", b"Notification", b"Session",
         b"Lobby", b"Party", b"Room", b"Clan", b"UserStorage", b"Achievements"]
print("=== 服务名字符串偏移 ===")
str_off = {}
for n in names:
    offs = []
    i = 0
    while True:
        p = data.find(n, i)
        if p < 0:
            break
        # 确认是独立串（前后是 NUL 或非字母）
        ok = (p == 0 or not (65 <= data[p-1] <= 90 or 97 <= data[p-1] <= 122)) and \
             (p+len(n) >= len(data) or data[p+len(n)] == 0)
        if ok:
            offs.append(p)
        i = p + 1
    str_off[n] = offs
    print("  %-16s %s" % (n.decode(), ["0x%X" % o for o in offs[:6]]))

# 2) 找指向这些字符串的指针（VA 形式），看指针附近是否有服务号
print("\n=== 指向服务名串的指针（VA 4字节小端），指针附近 ±16 的整数 ===")
for n, offs in str_off.items():
    for so in offs[:3]:
        va = so + BASE
        ptr = struct.pack("<I", va)
        j = 0
        while True:
            p = data.find(ptr, j)
            if p < 0:
                break
            # 读指针位置前后 32 字节
            lo = max(0, p - 16)
            ctx = data[lo:p+20]
            ints = [struct.unpack_from("<I", data, p + k)[0] for k in (-8,-4,4,8,12) if 0 <= p+k <= len(data)-4]
            print("  %-14s ptr@0x%X ctx_ints=%s" % (n.decode(), p, ["0x%X" % x for x in ints]))
            j = p + 1
            if j - p > 0 and (data.count(ptr, 0, j) > 5):
                break

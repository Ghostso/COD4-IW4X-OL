#!/usr/bin/env python3
"""测试假设: Demonware 服务号 = hash(服务名) 的某种形式。
已知锚点(来自语料): matchmaking=21, marketplace=80/93, messaging=6, task=28,
stats=4, friends=9, room/party=11, telemetry=71, tencent=68, 未知=102, 3, 8, 10, 29。
试多种哈希/取模, 看能否把名字映到这些数。"""
import zlib
import hashlib

names = ["matchmaking","marketplace","messaging","task","stats","friends",
         "room","party","lobby","tencent","leaderboard","profiles","storage",
         "pooledstorage","teams","titleutilities","reward","eventlog","teams",
         "session","presence","notification","clan","achievements","userstorage",
         "content","unlock","inventory","store","wallet"]

def fnv1a32(b):
    h=0x811C9DC5
    for c in b:
        h^=c; h=(h*0x01000193)&0xFFFFFFFF
    return h
def fnv1_32(b):
    h=0x811C9DC5
    for c in b:
        h=(h*0x01000193)&0xFFFFFFFF; h^=c
    return h
def djb2(b):
    h=5381
    for c in b: h=((h*33)+c)&0xFFFFFFFF
    return h
def sdbm(b):
    h=0
    for c in b: h=(c+(h<<6)+(h<<16)-h)&0xFFFFFFFF
    return h
def crc32(b): return zlib.crc32(b)&0xFFFFFFFF
def md5_32(b): return int.from_bytes(hashlib.md5(b).digest()[:4],"little")
def sha1_32(b): return int.from_bytes(hashlib.sha1(b).digest()[:4],"little")
def sha256_32(b): return int.from_bytes(hashlib.sha256(b).digest()[:4],"little")

hashes = {"fnv1a":fnv1a32,"fnv1":fnv1_32,"djb2":djb2,"sdbm":sdbm,"crc32":crc32,
          "md5":md5_32,"sha1":sha1_32,"sha256":sha256_32}

# 目标: 对每个已知名字, 看哪个 (hash, mod) 能得到已知服务号
known = {"matchmaking":21,"marketplace":80,"messaging":6,"stats":4,"friends":9,
         "room":11,"party":11,"tencent":68,"leaderboard":102}
print("=== 单哈希直接取低字节/取模匹配 ===")
for hn, hf in hashes.items():
    for n, tgt in known.items():
        for suffix in ("", "\x00"):
            h = hf((n+suffix).encode())
            cand = [("&0xFF", h&0xFF), ("%256", h%256), ("%100", h%100),
                    ("%128", h%128), ("%251", h%251)]
            for label, v in cand:
                if v == tgt:
                    print("  HIT %-10s %-16s %-12s -> %d" % (hn, n, label, v))

print("\n=== 打印每个名字的 8 种哈希 (低字节) 供人工比对 ===")
print("%-16s" % "name" + "".join("%10s" % k for k in hashes))
for n in names:
    row = "%-16s" % n
    for hn in hashes:
        h = hashes[hn](n.encode())
        row += "%10d" % (h & 0xFF)
    print(row)

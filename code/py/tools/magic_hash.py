#!/usr/bin/env python3
"""两魔数是否 = 某字符串的哈希/CRC。候选串来自 playlist/地图/mode 名。"""
import hashlib
import zlib

A = 0xD692ADAB
B = 0x8D51E398
As = A - 2**32
Bs = B - 2**32

cands = [
    "mp_playlists_shipRetail_1.0.0.info", "mp_playlists_shipRetail", "playlist",
    "M7-E8S6Client", "1625160", "D4-93-90-18-55-10", "the.json",
    "coop_train_mp_firingrange", "mp_firingrange", "firingrange",
    "g_gametype coop", "coop", "tdm", "dm", "war", "sd", "ctf", "dom", "koth",
    "TDM", "DM", "WAR", "SD", "CTF", "DOM", "KOTH", "FFA", "HQ",
    "shipRetail", "1.0.0", "1649370", "10", "50", "20",
]


def fnv1a(d):
    h = 0x811C9DC5
    for c in d:
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def fnv1(d):
    h = 0x811C9DC5
    for c in d:
        h = (h * 0x01000193) & 0xFFFFFFFF
        h ^= c
    return h


def djb2(d):
    h = 5381
    for c in d:
        h = ((h * 33) + c) & 0xFFFFFFFF
    return h


def java(d):
    h = 0
    for c in d:
        h = (31 * h + c) & 0xFFFFFFFF
    return h


def sdbm(d):
    h = 0
    for c in d:
        h = (c + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


algs = {"crc32": lambda d: zlib.crc32(d) & 0xFFFFFFFF,
        "fnv1a": fnv1a, "fnv1": fnv1, "djb2": djb2, "java": java, "sdbm": sdbm,
        "adler32": lambda d: zlib.adler32(d) & 0xFFFFFFFF}

print("A target = 0x%08X (signed %d)" % (A, As))
print("B target = 0x%08X (signed %d)" % (B, Bs))

hits = 0
for s in cands:
    for enc in ("utf-8", "utf-16-le"):
        d = s.encode(enc)
        for an, f in algs.items():
            v = f(d)
            if v in (A, B):
                print("  MATCH %s %s %r -> 0x%08X" % (an, enc, s, v))
                hits += 1
        for an in ("md5", "sha1", "sha256"):
            dig = getattr(hashlib, an)(d).digest()
            for nm, v in [("lo_le", int.from_bytes(dig[:4], "little")),
                          ("lo_be", int.from_bytes(dig[:4], "big"))]:
                if v in (A, B):
                    print("  MATCH %s-%s %s %r -> 0x%08X" % (an, nm, enc, s, v))
                    hits += 1
print("\n命中数 = %d" % hits)

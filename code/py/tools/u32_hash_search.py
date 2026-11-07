#!/usr/bin/env python3
"""31902622 与 MAC 的更多哈希算法（FNV1a/32, djb2, sdbm, Java hashCode）。"""
import hashlib

target = 31902622
cands = {
    "mac_str": b"D4-93-90-18-55-10",
    "mac_hex": b"D49390185510",
    "mac_lower": b"d4-93-90-18-55-10",
    "mac_nodash": b"D49390185510",
}


def fnv1a32(d):
    h = 0x811C9DC5
    for c in d:
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def fnv132(d):
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


def sdbm(d):
    h = 0
    for c in d:
        h = (c + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


def java(d):
    h = 0
    for c in d:
        h = (31 * h + c) & 0xFFFFFFFF
    return h


print("target = %d = 0x%08X" % (target, target))
for name, d in cands.items():
    print("\n-- %s --" % name)
    for fn, f in [("fnv1a32", fnv1a32), ("fnv132", fnv132), ("djb2", djb2), ("sdbm", sdbm), ("java", java)]:
        v = f(d)
        print("   %-8s 0x%08X %s" % (fn, v, "<<< MATCH" if v == target else ""))
    for alg in ("md5", "sha1", "sha256"):
        dig = getattr(hashlib, alg)(d).digest()
        for nm, v in [("lo_le", int.from_bytes(dig[:4], "little")),
                      ("lo_be", int.from_bytes(dig[:4], "big")),
                      ("hi_le", int.from_bytes(dig[-4:], "little")),
                      ("hi_be", int.from_bytes(dig[-4:], "big"))]:
            print("   %-6s %-5s 0x%08X %s" % (alg, nm, v, "<<< MATCH" if v == target else ""))

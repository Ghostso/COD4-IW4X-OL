#!/usr/bin/env python3
"""魔数 A/B 是否为账号/用户名相关哈希：用账号ID的多种字节形态做输入。"""
import hashlib
import itertools
import zlib

A = 0xD692ADAB
B = 0x8D51E398
ACCu = 0xE7C8A98A6B4C2D0E
targets = {A: "A", B: "B"}


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


algs = {"crc32": lambda d: zlib.crc32(d) & 0xFFFFFFFF, "fnv1a": fnv1a, "fnv1": fnv1,
        "djb2": djb2, "java": java, "sdbm": sdbm}

inputs = {
    "acc_le8": ACCu.to_bytes(8, "little"),
    "acc_be8": ACCu.to_bytes(8, "big"),
    "acc_le4": (ACCu & 0xFFFFFFFF).to_bytes(4, "little"),
    "acc_str": str(ACCu).encode(),
    "acc_str_hex": ("%X" % ACCu).encode(),
    "user": b"M7-E8S6Client",
    "chan": (0x1122334455667788).to_bytes(8, "little"),
    "chan_str": b"1234605616436508552",
}

hits = 0
for nm, d in inputs.items():
    for an, f in algs.items():
        v = f(d)
        if v in targets:
            print("MATCH %s(%s) = 0x%08X = %s" % (an, nm, v, targets[v]))
            hits += 1
    for an in ("md5", "sha1", "sha256"):
        dig = getattr(hashlib, an)(d).digest()
        for lab, v in [("lo_le", int.from_bytes(dig[:4], "little")),
                       ("lo_be", int.from_bytes(dig[:4], "big")),
                       ("hi_le", int.from_bytes(dig[-4:], "little")),
                       ("hi_be", int.from_bytes(dig[-4:], "big"))]:
            if v in targets:
                print("MATCH %s-%s(%s) = 0x%08X = %s" % (an, lab, nm, v, targets[v]))
                hits += 1

# 也测 "253009291" 等 variant2 值
V2 = [253009291, -113504840, -679341779]
print("\n命中 = %d" % hits)
print("\nvariant2 值 hex:")
for v in V2:
    print("  %d = 0x%08X" % (v, v & 0xFFFFFFFF))

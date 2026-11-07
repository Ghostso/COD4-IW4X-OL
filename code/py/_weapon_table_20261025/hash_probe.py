# -*- coding: utf-8 -*-
"""Identify the hash function used by CODOL stringtable cells.

Takes a known cell (string_hash, other) pair from mp/coweaponattachmenttable.csv
and searches all NUL-terminated strings in the zone for a match under several
common hash variants.
"""
import re, sys, io, zlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
TARGETS = {0x30293b65: 'cell0_field0', 0xb38d3461: 'cell0_field1'}

d = open(ZONE, 'rb').read()


def h17(s):  # hash*17 + c  (CoD4 style)
    h = 0
    for c in s:
        h = (h * 17 + c) & 0xFFFFFFFF
    return h


def h33(s):
    h = 0
    for c in s:
        h = (h * 33 + c) & 0xFFFFFFFF
    return h


def h31(s):
    h = 0
    for c in s:
        h = (h * 31 + c) & 0xFFFFFFFF
    return h


def hdjb2(s):
    h = 5381
    for c in s:
        h = (h * 33 + c) & 0xFFFFFFFF
    return h


def hfnv(s):
    h = 0x811C9DC5
    for c in s:
        h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF
    return h


def hsdbm(s):
    h = 0
    for c in s:
        h = (c + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


FUNCS = {
    'h17': h17, 'h33': h33, 'h31': h31, 'djb2': hdjb2, 'fnv1a': hfnv, 'sdbm': hsdbm,
    'crc32': lambda s: zlib.crc32(s) & 0xFFFFFFFF,
    'h17lower': lambda s: h17(bytes(c | 0x20 if 65 <= c <= 90 else c for c in s)),
    'h33lower': lambda s: h33(bytes(c | 0x20 if 65 <= c <= 90 else c for c in s)),
    'h31lower': lambda s: h31(bytes(c | 0x20 if 65 <= c <= 90 else c for c in s)),
    'crc32lower': lambda s: zlib.crc32(bytes(c | 0x20 if 65 <= c <= 90 else c for c in s)) & 0xFFFFFFFF,
}

found = {}
seen = set()
for m in re.finditer(rb'[ -~]{3,200}', d):
    s = m.group()
    if s in seen:
        continue
    seen.add(s)
    for name, fn in FUNCS.items():
        v = fn(s)
        if v in TARGETS:
            found.setdefault((name, v), []).append(s.decode('latin-1'))

for k, v in found.items():
    print(k, TARGETS[k[1]], v[:5])
print('distinct strings scanned', len(seen))

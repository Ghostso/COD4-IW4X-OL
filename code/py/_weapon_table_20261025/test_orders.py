# -*- coding: utf-8 -*-
"""Test candidate registration orders against two known engine indices.

Known (ol-mod devlog, live run): m4a1tech_mp -> native asset 165,
fa1911ncm_mp -> 77. Difference = 88.
"""
import csv, struct, re, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
BASE = os.path.join(ROOT, '_weapon_table_20261025')
ST = os.path.join(BASE, 'st')
ZONE = os.path.join(BASE, 'common_mp.zone')

A, B = 'm4a1tech_mp', 'fa1911ncm_mp'
WANT = {A: 165, B: 77}


def first_appearance(path, col=0):
    order, seen = [], set()
    for row in csv.reader(open(path, encoding='utf-8')):
        if len(row) <= col:
            continue
        v = row[col]
        if v and v not in seen:
            seen.add(v)
            order.append(v)
    return order


def zone_order():
    d = open(ZONE, 'rb').read()
    KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
    NAME = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')
    out = []
    for i in range(8557):
        typ, off, ptr, size = struct.unpack_from('<4I', d, 0xFC24 + i * 16)
        if typ != 28:
            continue
        b = d[0x28 + off: 0x28 + off + size]
        m = KEY.search(b)
        if m:
            out.append(m.group(1).decode().lower() + '_mp')
        else:
            m2 = NAME.search(b)
            out.append(m2.group(1).decode().lower() if m2 else '')
    return out


cands = {
    'zone type-28 order': zone_order(),
    'attachmenttable col0': first_appearance(os.path.join(ST, 'mp_coweaponattachmenttable.csv'), 0),
    'uislottable col0': first_appearance(os.path.join(ST, 'mp_coweaponuislottable.csv'), 0),
    'altlookup col0': first_appearance(os.path.join(ST, 'mp_alt_weapon_lookup_table.csv'), 0),
    'altlookup col1': first_appearance(os.path.join(ST, 'mp_alt_weapon_lookup_table.csv'), 1),
}

for label, order in cands.items():
    idx = {}
    for i, v in enumerate(order):
        idx.setdefault(v, i)
    pa, pb = idx.get(A), idx.get(B)
    print('%-24s n=%-5d %s=%-5s %s=%-5s diff=%s'
          % (label, len(order), A, pa, B, pb,
             (pa - pb) if (pa is not None and pb is not None) else 'n/a'))

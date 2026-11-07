# -*- coding: utf-8 -*-
"""Is col55 = rank of the weapon in zone order restricted to the col55 table's
own name set?  If so, the table IS an index table, just ordered differently."""
import csv, struct, re, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
rows = list(csv.reader(open(BASE + r'\st_market\mp_coweapitemswea.csv', encoding='utf-8')))


def key(r):
    k = r[1]
    if k.startswith('SF_WEAPON_') and k.endswith('_MP_NAME'):
        return k[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return None


num = {}
order_in_table = []
for i, r in enumerate(rows):
    k = key(r)
    if k:
        order_in_table.append(k)
        if len(r) > 55 and r[55].isdigit():
            num.setdefault(k, int(r[55]))

z = open(BASE + r'\common_mp.zone', 'rb').read()
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
zone = []
for i in range(8557):
    t, off, ptr, sz = struct.unpack_from('<4I', z, 0xFC24 + i * 16)
    if t != 28:
        continue
    b = z[0x28 + off: 0x28 + off + sz]
    m = KEY.search(b)
    nm = m.group(1).decode().lower() + '_mp' if m else None
    zone.append(nm)

# rank of each name within zone order restricted to the table's own name set
table_set = set(order_in_table)
rank = {}
k = 0
for n in zone:
    if n in table_set:
        rank.setdefault(n, k)
        k += 1
print('zone-restricted rank count', len(rank))

mism = 0
tot = 0
for n, v in num.items():
    if n in rank:
        tot += 1
        if rank[n] != v:
            mism += 1
print('compare col55 vs zone-restricted rank: total', tot, 'mismatch', mism)
for n in list(num)[:10]:
    if n in rank:
        print('  %-26s col55=%-4d rank=%-4d' % (n, num[n], rank[n]))

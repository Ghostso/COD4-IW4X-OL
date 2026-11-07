# -*- coding: utf-8 -*-
"""Correlate coWeapItemsWEA col55 against several orderings to see what it is."""
import csv, struct, re, io, sys, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
rows = list(csv.reader(open(BASE + r'\st_market\mp_coweapitemswea.csv', encoding='utf-8')))


def key(r):
    k = r[1]
    if k.startswith('SF_WEAPON_') and k.endswith('_MP_NAME'):
        return k[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return None


col55 = {}
for r in rows:
    k = key(r)
    if k and len(r) > 55 and r[55].isdigit():
        col55.setdefault(k, int(r[55]))
print('col55 entries', len(col55))
nums = sorted(col55.values())
print('range', nums[0], nums[-1], 'distinct', len(set(nums)))

# zone order
z = open(BASE + r'\common_mp.zone', 'rb').read()
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
zone = []
for i in range(8557):
    t, off, ptr, sz = struct.unpack_from('<4I', z, 0xFC24 + i * 16)
    if t != 28:
        continue
    b = z[0x28 + off: 0x28 + off + sz]
    m = KEY.search(b)
    zone.append(m.group(1).decode().lower() + '_mp' if m else None)
zpos = {}
for k, n in enumerate(zone):
    if n:
        zpos.setdefault(n, k)
print('zone named', len(zpos))

pairs = [(col55[n], zpos[n]) for n in col55 if n in zpos]
print('overlap', len(pairs))
if len(pairs) > 10:
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    print('pearson r = %.4f' % (num / den if den else 0))
    for a, b in sorted(pairs)[:15]:
        print('   col55=%-4d zone_pos=%-4d' % (a, b))

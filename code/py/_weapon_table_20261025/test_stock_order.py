# -*- coding: utf-8 -*-
"""Test: is the stock weapon index = position in common_mp zone order, counting
only weapons that also have their own .ff in ff_init_weapons_V37.ifs?"""
import struct, re, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

IFS = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\IIPSDownload\ff_init_weapons_V37.ifs'
ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone'

d = open(IFS, 'rb').read()
hdr = struct.unpack_from('<I', d, 4)[0]
man = d[hdr:d.find(b'IWff0100', hdr)].decode('latin-1', 'replace')
stock = set()
for line in man.splitlines():
    m = re.search(r'/([a-z0-9_]+)_mp\.ff$', line)
    if m:
        stock.add(m.group(1) + '_mp')
print('stock weapons in ff_init_weapons:', len(stock))

z = open(ZONE, 'rb').read()
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
NAME = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')
order = []
for i in range(8557):
    t, off, ptr, size = struct.unpack_from('<4I', z, 0xFC24 + i * 16)
    if t != 28:
        continue
    b = z[0x28 + off: 0x28 + off + size]
    m = KEY.search(b)
    nm = m.group(1).decode().lower() + '_mp' if m else (
        NAME.search(b).group(1).decode().lower() if NAME.search(b) else '')
    order.append(nm)
print('zone weapons:', len(order))

seq = [n for n in order if n in stock]
print('zone order filtered to stock set:', len(seq))

for probe, want in (('m4a1tech_mp', 165), ('fa1911ncm_mp', 77),
                    ('m4a1techcommon_mp', None), ('m9_mp', None)):
    pos = [k for k, v in enumerate(seq) if v == probe]
    print('  %-20s pos=%s want=%s' % (probe, pos, want))

print('\nfirst 30 of the filtered sequence:')
for k, n in enumerate(seq[:30]):
    print('  %3d %s' % (k, n))

# also try alphabetical
alpha = sorted(seq)
print('\nalphabetical positions:')
for probe in ('m4a1tech_mp', 'fa1911ncm_mp'):
    print('  %-20s %s' % (probe, [k for k, v in enumerate(alpha) if v == probe]))

# -*- coding: utf-8 -*-
"""Cross-check: do the '** <base> ...' base numbers land on real stock weapon
names in codol_weapon_index_3_19.csv?"""
import re, csv, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
stock = {}
for r in csv.DictReader(open(BASE + r'\codol_weapon_index_3_19.csv', encoding='utf-8-sig')):
    stock[int(r['engine_index'])] = r['name']

text = open(r'D:\BaiduNetdiskDownload\使命召唤OL\_LEARN_TESTOL_DELIVERY2\decoded\str-CodolGameServer.txt',
            'rb').read().decode('latin-1', 'replace')
bases = sorted({int(m.group(1)) for m in re.finditer(r'\*\*[ ]+(\d+)[ ]+\d+[ ]+\d+', text)})
print('distinct bases in modular strings:', len(bases))
hit = 0
for b in bases:
    nm = stock.get(b)
    if nm:
        hit += 1
    print('  base %-6d -> %s' % (b, nm or '<no stock weapon at this index>'))
print('\nresolved %d / %d' % (hit, len(bases)))

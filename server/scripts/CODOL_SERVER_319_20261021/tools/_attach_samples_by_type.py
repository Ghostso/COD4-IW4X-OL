import json,collections
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
bytype=collections.defaultdict(list)
for a in j['assets']:
    for r in a['records']:
        off=r['raw_offset']&0xffff
        if off<=0xbfc: bytype[r['type']].append((a['name'],r))
for k in [7,9,4,6,12,0]:
    print('\nTYPE',k)
    for nm,r in bytype[k][:30]: print(nm,'flags',hex(r['flags']),'off',hex(r['raw_offset']&0xffff),'val',hex(r['raw_value']))

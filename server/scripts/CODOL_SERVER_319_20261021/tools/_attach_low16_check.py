import json
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
bad=[]
for a in j['assets']:
    for r in a['records']:
        off=r['raw_offset']&0xffff
        if off>0xbfc: bad.append((a['name'],r['type'],hex(r['raw_offset']),hex(off)))
print('records',sum(len(a['records']) for a in j['assets']),'bad',len(bad))
for x in bad[:50]: print(x)

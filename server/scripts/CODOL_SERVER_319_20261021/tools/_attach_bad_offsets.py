import json,collections
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
c=collections.Counter()
for a in j['assets']:
 for r in a['records']:
  off=r['raw_offset']&0xffff
  if off>0xbfc:c[off]+=1
for k,v in c.most_common(100): print(hex(k),v)

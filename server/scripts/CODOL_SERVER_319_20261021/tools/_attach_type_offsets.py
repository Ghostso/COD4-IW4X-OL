import json,collections
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
bytype=collections.defaultdict(lambda:[0,0,0])
for a in j['assets']:
 for r in a['records']:
  off=r['raw_offset']&0xffff; k=r['type']
  bytype[k][0]+=1
  if off<=0xbfc:bytype[k][1]+=1
  else:bytype[k][2]+=1
for k,(n,good,bad) in sorted(bytype.items()): print(k,'n',n,'<=bfc',good,'>bfc',bad)

import json
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
for a in j['assets']:
    for r in a['records']:
        if r['type']==15: print(a['name'],r)

import json
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
for a in j['assets']:
    if a['extra']:
        print(a['name'],'count',a['count'],'extra',len(a['extra'])//2,a['extra'][:100])

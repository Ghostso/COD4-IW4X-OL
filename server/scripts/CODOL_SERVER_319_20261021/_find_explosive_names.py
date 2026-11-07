import json
j=json.load(open(r'fixtures\common_mp_weapondefs_20261023.json',encoding='utf-8'))
for r in j['weapons']:
    if 'mortar' in r['name'] or 'predator' in r['name'] or 'rpg' in r['name']:
        print(r['name'],hex(r['offset']),r['size'])

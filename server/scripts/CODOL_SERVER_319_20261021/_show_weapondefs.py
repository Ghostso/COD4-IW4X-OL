import json
j=json.load(open(r'fixtures\common_mp_weapondefs_20261023.json',encoding='utf-8'))
for r in j['firingrange']:
 print(r['name'],r['damage'],r['player_damage'],r['min_damage'],r['min_player_damage'],r['max_damage_range'],r['min_damage_range'])

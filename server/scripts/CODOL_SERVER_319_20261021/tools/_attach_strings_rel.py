import json
j=json.load(open(r'fixtures\common_mp_weaponattach_records_20261023.json',encoding='utf-8'))
for nm in ['fmj_base','highcal_base','silencer_m4','scope_none','akimbo_base','flashhider_base','heartbeat_base']:
    a=next(x for x in j['assets'] if x['name']==nm)
    print('\n',nm,'strings',a['trailing_strings'])
    for r in a['records']:
        print(r['type'],hex(r['raw_offset']),hex(r['raw_value']),r['flags'])

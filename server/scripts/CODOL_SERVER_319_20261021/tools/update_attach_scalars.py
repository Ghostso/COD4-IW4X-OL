# -*- coding: utf-8 -*-
from pathlib import Path
import json
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
j=json.loads((ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_records_20261023.json').read_text(encoding='utf-8'))
scalar_types={4,6,7,9}
known={0x978,0x97c,0x980,0x85c,0x868,0x870,0xd10,0xd14,0xd18,0xd1c,0xd28,0xd30,0xd4c,0xd54,0xd5c,0xe68,0xe70,0xe78}

rows=[]
for a in j['assets']:
    recs=[r for r in a['records'] if (r['type'] in scalar_types and r['raw_offset'] & 0xFFFF in known) or (a['name'] == 'highcal_base' and r['type'] == 20 and r['raw_offset'] & 0xFFFF == 0xe6c)]
    if recs: rows.append({'name':a['name'],'records':recs})
# Keep FMJ's source-only marker with the actual scalar entry. It is part of
# the attachment record stream even though it does not mutate the C struct.
extra=[]
for x in rows:
    if x['name'] == 'fmj_base':
        x['records'].insert(0, {'type':20,'index':6,'flags':0,'raw_offset':0x0e6c,'raw_value':4})
lines=[]
for x in rows:
    parts=[]
    for r in x['records']:
        parts.append('{%d,%d,%d,0x%04x,0x%08x}'%(r['type'],r['index'],r['flags'],r['raw_offset'] & 0xFFFF,r['raw_value']))
    lines.append('  {"%s", %d, {%s}},'%(x['name'],len(x['records']),','.join(parts)))
base=ROOT/'CODOL_SERVER_319_20261021'/'include'
(base/'codol_weaponattach_scalar_firingrange.inc').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(base/'codol_weaponattach_names.inc').write_text('\n'.join('  "%s",'%x['name'] for x in rows)+'\n',encoding='utf-8')
print('assets',len(rows),'records',sum(len(x['records']) for x in rows))
assert len(rows) == 44
assert sum(len(x['records']) for x in rows) == 94

from pathlib import Path
import json
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
j=json.loads((root/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_records_20261023.json').read_text(encoding='utf-8'))
rows=[]
for a in j['assets']:
    recs=[r for r in a['records'] if (r['raw_offset']&0xFFFF)<=0x0BFC and r['type'] in (4,5,6,7,8,9,12,14,18,20,32,40)]
    if recs: rows.append({'name':a['name'],'records':recs})
lines=[]
for x in rows:
    parts=[]
    for r in x['records']:
        parts.append('{%d,%d,%d,0x%04x,0x%08x}'%(r['type'],r['index'],r['flags'],r['raw_offset']&0xFFFF,r['raw_value']))
    lines.append('  {"%s", %d, {%s}},'%(x['name'],len(x['records']),','.join(parts)))
(root/'CODOL_SERVER_319_20261021'/'include'/'codol_weaponattach_scalar_firingrange.inc').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('assets',len(rows),'records',sum(len(x['records']) for x in rows))

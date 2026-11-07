from pathlib import Path
import json
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
inc=root/'CODOL_SERVER_319_20261021'/'include'/'codol_weaponattach_firingrange.inc'
j=json.loads((root/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_records_20261023.json').read_text(encoding='utf-8'))
rows=[]
for a in j['assets']:
    ok=True
    for r in a['records']:
        if r['field_offset']>0xbfc:
            ok=False; break
    if ok and a['count']==len(a['records']): rows.append(a)
lines=[]
for a in sorted(rows,key=lambda x:x['name']):
    lines.append('  {"%s", %d, {'%(a['name'],a['count']))
    for r in a['records']:
        lines.append('    {%d,%d,%d,0x%05x,0x%08x},'%(r['type'],r['index'],r['flags'],r['field_offset'],r['raw_value']))
    lines.append('  },')
inc.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('attachments',len(rows),'wrote',inc)

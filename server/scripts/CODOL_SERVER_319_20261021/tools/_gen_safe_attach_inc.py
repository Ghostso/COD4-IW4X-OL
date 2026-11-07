from pathlib import Path
import json,struct,math
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
j=json.loads((root/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_records_20261023.json').read_text(encoding='utf-8'))
rows=[]; dropped=0
for a in j['assets']:
    recs=[]
    for r in a['records']:
        off=r['raw_offset']&0xffff
        if r['type'] not in (4,5,6,7,9): dropped+=1; continue
        if off>0x0bfc: dropped+=1; continue
        if r['type'] in (4,5,6):
            v=struct.unpack_from('<i',struct.pack('<I',r['raw_value']))[0]
            if v<0 or v>0x7fffffff: dropped+=1; continue
        if r['type'] in (7,9):
            f=struct.unpack_from('<f',struct.pack('<I',r['raw_value']))[0]
            if not math.isfinite(f): dropped+=1; continue
        recs.append(r)
    if recs: rows.append({'name':a['name'],'records':recs})
lines=[]
for x in rows:
    parts=['{%d,%d,%d,0x%04x,0x%08x}'%(r['type'],r['index'],r['flags'],r['raw_offset']&0xffff,r['raw_value']) for r in x['records']]
    lines.append('  {"%s", %d, {%s}},'%(x['name'],len(x['records']),','.join(parts)))
(root/'CODOL_SERVER_319_20261021'/'include'/'codol_weaponattach_scalar_firingrange.inc').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('assets',len(rows),'records',sum(len(x['records']) for x in rows),'dropped',dropped)

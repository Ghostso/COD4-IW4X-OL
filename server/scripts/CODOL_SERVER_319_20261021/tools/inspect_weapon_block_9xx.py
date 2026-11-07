import struct,json
from pathlib import Path
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
d=(root/'run_codol_001/runs/PHASE7_STATIC_20261023/common_mp_zone.bin').read_bytes()
j=json.loads((root/'CODOL_SERVER_319_20261021/fixtures/common_mp_weapondefs_20261023.json').read_text(encoding='utf-8'))
for r in j['firingrange']:
    b=d[0x28+r['offset']:0x28+r['offset']+r['size']]
    ints=[struct.unpack_from('<i',b,o)[0] for o in range(0x984,0x9B0,4)]
    fs=[struct.unpack_from('<f',b,o)[0] for o in range(0x984,0x9B0,4)]
    print('%-18s %s | %s' % (r['name'],ints,' '.join('%.3f'%x for x in fs)))

import struct,json
from pathlib import Path
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
d=(root/'run_codol_001/runs/PHASE7_STATIC_20261023/common_mp_zone.bin').read_bytes()
j=json.loads((root/'CODOL_SERVER_319_20261021/fixtures/common_mp_weapondefs_20261023.json').read_text(encoding='utf-8'))
for w in j['firingrange'][:6]:
    b=d[0x28+w['offset']:0x28+w['offset']+w['size']]
    print('\n',w['name'], 'base',hex(w['offset']), 'size',len(b))
    # dump scalar heads where f32 plausible and location in weapon body
    for o in range(0x800,0xf00,4):
        if o+4>len(b): break
        u=struct.unpack_from('<I',b,o)[0]; f=struct.unpack_from('<f',b,o)[0]; i=struct.unpack_from('<i',b,o)[0]
        if o in range(0x880,0x9b0) or o in range(0xb80,0xd40) or o in range(0xe00,0xee0):
            if f==f and abs(f) < 1e7:
                print('%04x %08x %7d %.7g' % (o,u,i,f))

import struct, os, json
d=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_114204\engine'
sent=open(os.path.join(d,'sentinel_table.bin'),'rb').read()
rows=[]
for i in range(0,len(sent),4):
    v=struct.unpack_from('<I',sent,i)[0]
    if v: rows.append((0x00CA8000+i,v))
print('sentinel nonzero',len(rows))
from collections import Counter
c=Counter(v>>16<<16 for s,v in rows if 0x10000000<=v<0x14000000)
print('runtime-code pointers:')
for k,n in sorted(c.items()): print('  %08x x%d'%(k,n))
print('first 40 slot->target:')
for s,v in rows[:40]: print('  %08x -> %08x'%(s,v))

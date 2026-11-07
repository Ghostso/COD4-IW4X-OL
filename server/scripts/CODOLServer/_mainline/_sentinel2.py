import struct, os, csv
d=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_112143\engine'
p=os.path.join(d,'sentinel_table.bin')
b=open(p,'rb').read()
rows=[]
for i in range(0,len(b),4):
    v=struct.unpack_from('<I',b,i)[0]
    if v: rows.append((0x00CA8000+i,v))
print('sentinel nonzero',len(rows))
print('first 100:')
for s,v in rows[:100]: print('%08x -> %08x'%(s,v))
from collections import Counter
c=Counter(v>>16<<16 for s,v in rows if 0x10000000<=v<0x14000000)
print('high blocks:')
for k,n in sorted(c.items()): print('  %08x x%d'%(k,n))
print('other ranges:')
c2=Counter(v>>16<<16 for s,v in rows if not(0x10000000<=v<0x14000000))
for k,n in sorted(c2.items()): print('  %08x x%d'%(k,n))
out=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\sentinel_runtime_map_20260925_112143.csv'
with open(out,'w',encoding='utf-8') as f:
    f.write('slot_va,target_va\n')
    for s,v in rows: f.write('0x%08X,0x%08X\n'%(s,v))
print('wrote',out)

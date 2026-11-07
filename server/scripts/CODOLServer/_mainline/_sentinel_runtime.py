import struct, json, os
b=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine\engine_best.bin','rb').read()
base=0x00994000
tbl_va=0x00ca8000
tbl_off=tbl_va-base
rows=[]
for i in range(0,0x1000,4):
    v=struct.unpack_from('<I',b,tbl_off+i)[0]
    if v:
        rows.append((tbl_va+i,v))
print('nonzero sentinel slots',len(rows))
print('first 80:')
for s,v in rows[:80]:
    print('%08x -> %08x' % (s,v))
# target distribution
from collections import Counter
c=Counter()
for s,v in rows:
    if 0x00400000 <= v < 0x00f00000:
        c[v]+=1
print('distinct targets',len(c),'top:')
for v,n in c.most_common(30):
    print('  %08x x%d' % (v,n))
# write csv
out=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\sentinel_runtime_map_20260925.csv'
with open(out,'w',encoding='utf-8') as f:
    f.write('slot_va,target_va\n')
    for s,v in rows:
        f.write('0x%08X,0x%08X\n'%(s,v))
print('wrote',out)

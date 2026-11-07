import os, math, collections, struct
d=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_114204\engine'
code=open(os.path.join(d,'runtime_code.bin'),'rb').read()
sent=open(os.path.join(d,'sentinel_table.bin'),'rb').read()
def ent(b):
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
print('runtime_code size',len(code),'entropy %.4f'%ent(code))
# per-16-byte block entropy
blocks=[code[i:i+16] for i in range(0,len(code),16)]
es=[ent(b) for b in blocks if len(b)==16]
print('block ent min %.2f max %.2f mean %.2f'%(min(es),max(es),sum(es)/len(es)))
# how many distinct 16-byte blocks
print('distinct 16B blocks',len(set(bytes(b) for b in blocks)),'of',len(blocks))
# byte histogram top
c=collections.Counter(code)
print('top bytes',c.most_common(12))
# 0xCC / 0x00 density
print('zeros %d, int3 %d'%(code.count(0),code.count(0xCC)))
# check pointer density inside code: dwords that land in runtime range
ptrs=sum(1 for i in range(0,len(code)-4,4) if 0x10C00000<=struct.unpack_from('<I',code,i)[0]<0x11000000)
print('inline runtime pointers (4-aligned)',ptrs)

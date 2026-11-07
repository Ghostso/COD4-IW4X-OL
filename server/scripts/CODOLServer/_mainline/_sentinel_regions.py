import struct
from collections import Counter
b=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine\engine_best.bin','rb').read()
base=0x00994000
tbl_off=0x00ca8000-base
vals=[struct.unpack_from('<I',b,tbl_off+i)[0] for i in range(0,0x1000,4)]
c=Counter(v>>16<<16 for v in vals if 0x10000000 <= v < 0x14000000)
print('high (0x1xxxxxxx) mapping blocks:')
for k,n in sorted(c.items()):
    print('  %08x  x%d' % (k,n))
c2=Counter(v>>16<<16 for v in vals if 0x70000000 <= v < 0x80000000)
print('mid (0x7xxxxxxx) mapping blocks:')
for k,n in sorted(c2.items()):
    print('  %08x  x%d' % (k,n))
others=[v for v in vals if v and not(0x10000000<=v<0x14000000) and not(0x70000000<=v<0x80000000)]
print('other nonzero values:', len(others))
for v in sorted(set(others))[:40]:
    print('  %08x' % v)

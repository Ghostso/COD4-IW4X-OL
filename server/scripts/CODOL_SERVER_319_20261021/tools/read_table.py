import struct
from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin')
d=p.read_bytes(); base=0x400000
for a,n in [(0xe605c0,80),(0xe5f918,80)]:
 print('===',hex(a))
 for i in range(n//4):
  print('%08x %08x'%(a+i*4,struct.unpack_from('<I',d,a-base+i*4)[0]))

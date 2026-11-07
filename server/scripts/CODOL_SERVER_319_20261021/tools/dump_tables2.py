import struct
from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin')
d=p.read_bytes(); b=0x400000
for a in (0x82c48a8,0x1e2d338,0xe5c4a8,0xe5c560,0xe5c978):
 vals=struct.unpack_from('<60I',d,a-b)
 print('===',hex(a))
 print(' '.join('%08x'%v for v in vals))

import struct
from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin')
d=p.read_bytes(); b=0x400000
for target in [0x49da10,0x49d760,0x49cb60,0x49cc70,0x49d710,0x49c870,0x49c790,0x49c620]:
    hits=[]; pos=0
    # direct call E8 rel32
    while True:
        i=d.find(b'\xe8',pos)
        if i<0: break
        if i+5<=len(d):
            rel=struct.unpack_from('<i',d,i+1)[0]
            if (i+b+5+rel)&0xffffffff==target: hits.append(i+b)
        pos=i+1
    print(hex(target),len(hits),[hex(x) for x in hits[:30]])

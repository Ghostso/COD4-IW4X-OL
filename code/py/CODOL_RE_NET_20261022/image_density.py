import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
for start in range(0,len(d),0x1000000):
    seg=d[start:start+0x1000000]
    nz=sum(1 for b in seg if b)
    print('%#010x-%#010x nonzero=%d (%.1f%%)'%(BASE+start,BASE+min(start+0x1000000,len(d)),nz,100.0*nz/max(1,len(seg))))

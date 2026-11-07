import struct
d=open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read();B=0x400000
def find_calls(target):
    res=[];start,end=0x1000,0x8A689A
    for i in range(start,end-5):
        if d[i]==0xE8:
            rel=struct.unpack_from('<i',d,i+1)[0]
            if ((B+i+5+rel)&0xffffffff)==target: res.append(B+i)
    return res
for t in [0xBB18B0,0x77FBF0,0x77FCD0,0xAD6D50,0xBB12A0]:
    print('%#010x called from %s'%(t,[hex(x) for x in find_calls(t)[:20]]))

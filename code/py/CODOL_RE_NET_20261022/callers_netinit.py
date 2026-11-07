import struct
d=open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read();B=0x400000
def callers(t,hi=0x8A689A):
    r=[]
    for i in range(0x1000,hi-5):
        if d[i]==0xE8:
            rel=struct.unpack_from('<i',d,i+1)[0]
            if ((B+i+5+rel)&0xffffffff)==t: r.append(B+i)
    return r
for t in [0x77EE40,0x77FCD0,0x77FBF0,0x63E750,0x641BE0,0x641900]:
    print(hex(t),'<-',[hex(x) for x in callers(t)])
pat=struct.pack('<I',0x82E1580);h=[];i=0
while True:
    i=d.find(pat,i)
    if i<0: break
    v=B+i
    if 0x401000<=v<0xE5C8000: h.append(v)
    i+=1
print('refs 82E1580',[hex(x) for x in h])

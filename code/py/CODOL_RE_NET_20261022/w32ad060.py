import struct
d=open("run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin","rb").read()
B=0x400000
out=[]
for i in range(0x1000,0x8A6890):
    if d[i]==0xC7 and d[i+1]==0x05 and struct.unpack_from("<I",d,i+2)[0]==0x32AD060:
        out.append("W %#010x imm=%#010x"%(B+i,struct.unpack_from("<I",d,i+6)[0]))
    if d[i]==0x89 and d[i+1]==0x05 and struct.unpack_from("<I",d,i+2)[0]==0x32AD060:
        out.append("W %#010x reg"%(B+i))
print(len(out))
print("`n".join(out[:30]))

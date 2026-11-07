import struct
d=open("run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin","rb").read()
B=0x400000
out=[]
for i in range(0x1000,0x8A6890):
    if d[i] in (0xC7,0x89,0xA3,0x66,0x88):
        for off in (1,2):
            try:
                t=struct.unpack_from("<I",d,i+off)[0]
            except Exception:
                continue
            if t==0x32AD064:
                out.append("%#010x op=%02X"%(B+i,d[i]))
print(len(out))
print("`n".join(out[:40]))

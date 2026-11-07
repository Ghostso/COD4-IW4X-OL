import struct
d = open(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B = 0x400000
def callers(t):
    r=[]
    for i in range(0x1000,0x8A6890):
        if d[i]==0xE8:
            rel=struct.unpack_from("<i",d,i+1)[0]
            if ((B+i+5+rel)&0xffffffff)==t:
                r.append(B+i)
    return r
print("callers of WriteDeltaStruct 0x670FF0:")
for c in callers(0x670FF0):
    print("  ", hex(c), "prev:", d[c-B-14:c-B].hex(" "))

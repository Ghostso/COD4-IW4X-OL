import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin"); LO=0x00010000
data=open(p,"rb").read()
def refs(t):
    pat=struct.pack("<I",t); out=[];k=0
    while True:
        k=data.find(pat,k)
        if k<0: break
        out.append(LO+k); k+=1
        if len(out)>200: break
    return out
for t in (0x00BA4430,0x00BA41D0):
    r=refs(t)
    mod=[a for a in r if 0x400000<=a<0x400000+0x0E659000]
    heap=[a for a in r if a>=0x400000+0x0E659000]
    print("0x%08X total=%d  in-module=%d  outside=%d"%(t,len(r),len(mod),len(heap)))
    for a in heap[:6]:
        o=a-LO
        ctx=data[o-16:o+16]
        print("     outer=0x%08X ctx=%s"%(a,ctx.hex(" ")))

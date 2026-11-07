import struct, sys, json, os
p=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump\snap_002.bin"
cov=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump\snap_002_cover.bin"
LO=0x00010000
print("file:",os.path.getsize(p))
targets={
 0x00DC78F0:"MyEventHandler_vtable",
 0x00DC795C:"dwRoomMatchUber_vtable",
 0x00DC7274:"dwRoomImp_vtable",
}
data=open(p,"rb").read()
print("read",len(data))
for va,name in targets.items():
    pat=struct.pack("<I",va)
    hits=[]
    i=0
    while True:
        i=data.find(pat,i)
        if i<0: break
        hits.append(LO+i)
        i+=4
        if len(hits)>40: break
    print("%-24s 0x%08X  dword-hits=%d  first=%s"%(name,va,len(hits),[hex(h) for h in hits[:8]]))

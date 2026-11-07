import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read()
LO=0x00010000
TEXT_HI=0x00E00000     # .text ends well below this
def scan(va,name):
    pat=struct.pack("<I",va); hits=[]; i=0
    while True:
        i=data.find(pat,i)
        if i<0: break
        a=LO+i
        hits.append(a); i+=1
    code=[h for h in hits if 0x00400000<=h<TEXT_HI]
    heap=[h for h in hits if h>=TEXT_HI]
    print("%-26s 0x%08X total=%3d code=%2d heap=%2d %s" % (
        name,va,len(hits),len(code),len(heap),
        ("heap:"+",".join(hex(h) for h in heap[:4])) if heap else ""))
    return heap
u=scan(0x00DC795C,"dwRoomMatchUber vt")
m=scan(0x00DC78F0,"MyEventHandler vt")
i=scan(0x00DC7274,"dwRoomImp vt")
# verify each heap candidate really is an object: read vt then check +0x68 == 0x63C5E0
print("\n-- verify dwRoomMatchUber candidates (object+0x68 should be 0x0063C5E0) --")
for a in u:
    off=(a+0x68)-LO
    if 0<=off<len(data)-4:
        v=struct.unpack_from("<I",data,off)[0]
        print("  obj@0x%08X  [+0x68]=0x%08X  %s"%(a,v,"MATCH" if v==0x63C5E0 else "no"))
print("\n-- verify MyEventHandler candidates +0x04 (slot1 should be 0x0063B500) --")
for a in m:
    off=(a+0x04)-LO
    v=struct.unpack_from("<I",data,off)[0] if 0<=off<len(data)-4 else None
    print("  obj@0x%08X [+0x04]=%s"%(a,hex(v) if v else "?"))

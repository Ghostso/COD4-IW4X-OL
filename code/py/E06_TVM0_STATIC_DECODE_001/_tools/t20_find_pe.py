import struct, pefile, io
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\lasttp3_blocks.bin"
d=open(p,"rb").read()
print("=== locate valid PE headers in the recovered last-.tp3 stream ===")
hits=[]
o=0
while True:
    i=d.find(b"MZ", o)
    if i<0: break
    o=i+1
    if i+0x40>len(d): continue
    try:
        e_lfanew,=struct.unpack_from("<I",d,i+0x3C)
    except Exception: continue
    if e_lfanew<0x40 or e_lfanew>0x400: continue
    j=i+e_lfanew
    if j+0x18>len(d): continue
    if d[j:j+4]!=b"PE\x00\x00": continue
    mach,=struct.unpack_from("<H",d,j+4)
    nsec,=struct.unpack_from("<H",d,j+6)
    tds,=struct.unpack_from("<I",d,j+8)
    opt,=struct.unpack_from("<H",d,j+0x14)
    ch,=struct.unpack_from("<H",d,j+0x16)
    hits.append((i,mach,nsec,opt,ch,tds))
    print("  MZ@0x%08X PE@+0x%X machine=0x%X nsec=%d optsize=0x%X chars=0x%X timestamp=0x%X" % (i,e_lfanew,mach,nsec,opt,ch,tds))
print("valid PE headers found:",len(hits))
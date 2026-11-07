import struct, pefile, io, hashlib
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\lasttp3_blocks.bin"
d=open(p,"rb").read()
print("=== carve embedded PE modules from recovered last-.tp3 stream ===")
offs=[]; o=0
while True:
    i=d.find(b"MZ",o)
    if i<0: break
    o=i+1
    if i+0x40>len(d): continue
    e,=struct.unpack_from("<I",d,i+0x3C)
    if 0x40<=e<=0x400 and d[i+e:i+e+4]==b"PE\x00\x00": offs.append(i)
for i in offs:
    # parse minimal header to get SizeOfImage
    e,=struct.unpack_from("<I",d,i+0x3C); j=i+e
    nsec,=struct.unpack_from("<H",d,j+6); optsz,=struct.unpack_from("<H",d,j+0x14)
    opt=j+0x18
    magic,=struct.unpack_from("<H",d,opt)
    # SizeOfImage at opt+56 for both PE32/PE32+
    soi,=struct.unpack_from("<I",d,opt+56)
    # compute max raw end
    maxend=0; names=[]
    for k in range(nsec):
        so=opt+optsz+k*40
        nm=d[so:so+8].rstrip(b"\x00").decode("latin1")
        vs,va,rs,rp=struct.unpack_from("<IIII",d,so+8)
        maxend=max(maxend,rp+rs); names.append(nm)
    blob=d[i:i+maxend]
    sz=len(blob)
    h=hashlib.sha256(blob).hexdigest()[:16]
    print("  MZ@0x%08X magic=0x%X nsec=%d SizeOfImage=0x%X carve=0x%X..0x%X (0x%X B) sha=%s" % (
        i,magic,nsec,soi,i,i+sz,sz,h))
    print("     sections: %s" % names)
    print("     embedded sha256(full carve)=%s" % hashlib.sha256(blob).hexdigest())
print()
print("total carved:",len(offs))
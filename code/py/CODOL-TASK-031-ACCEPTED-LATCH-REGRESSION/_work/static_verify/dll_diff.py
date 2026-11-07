import hashlib
a = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
b = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe.local\codoMP_client_shipRetailBase.dll"
da=open(a,'rb').read(); db=open(b,'rb').read()
print("A",len(da),hashlib.sha256(da).hexdigest())
print("B",len(db),hashlib.sha256(db).hexdigest())
print("same size:", len(da)==len(db))
diffs=[i for i in range(min(len(da),len(db))) if da[i]!=db[i]]
print("diff count:", len(diffs))
if diffs:
    lo,hi=min(diffs),max(diffs)
    print("range: 0x%X..0x%X" % (lo,hi))
    print("A:", " ".join("%02x"%x for x in da[lo:hi+1]))
    print("B:", " ".join("%02x"%x for x in db[lo:hi+1]))
    # map file offset to RVA
    import struct
    pe=struct.unpack_from("<I",da,0x3C)[0]
    nsec=struct.unpack_from("<H",da,pe+6)[0]
    opt=pe+24
    so=opt+struct.unpack_from("<H",da,opt)[0]
    for i in range(nsec):
        o=so+40*i
        vsz,vaddr,rsz,raddr=struct.unpack_from("<IIII",da,o+8)
        if raddr<=lo<raddr+rsz:
            print("file 0x%X -> section RVA 0x%X ; section rva_base=0x%X" % (lo, vaddr+(lo-raddr), vaddr))

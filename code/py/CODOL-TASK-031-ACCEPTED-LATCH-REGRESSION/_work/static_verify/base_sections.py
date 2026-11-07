import struct
p=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d=open(p,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]
mach,nsec=struct.unpack_from("<HH",d,pe+4)
opt=pe+24
imgbase=struct.unpack_from("<I",d,opt+28)[0]
sizeofimg=struct.unpack_from("<I",d,opt+56)[0]
print("machine",hex(mach),"nsec",nsec,"imagebase",hex(imgbase),"sizeofimage",hex(sizeofimg))
# section table
so=opt+struct.unpack_from("<H",d,opt)[0]
print("sections:")
for i in range(nsec):
    o=so+40*i
    nm=d[o:o+8].rstrip(b'\x00').decode('latin1')
    vsz,vaddr,rsz,raddr=struct.unpack_from("<IIII",d,o+8)
    print("  %-9s VA=%08X vsz=%08X raw=%08X rsz=%08X" % (nm,vaddr,vsz,raddr,rsz))

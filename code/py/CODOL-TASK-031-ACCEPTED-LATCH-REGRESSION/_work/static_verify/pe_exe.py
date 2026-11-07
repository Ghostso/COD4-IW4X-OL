import hashlib
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
d=open(p,'rb').read()
print("exe size",len(d),"sha256",hashlib.sha256(d).hexdigest())
import struct
pe=struct.unpack_from("<I",d,0x3C)[0]
mach,nsec=struct.unpack_from("<HH",d,pe+4)
opt=pe+24
imgbase=struct.unpack_from("<I",d,opt+28)[0]
sizeofimg=struct.unpack_from("<I",d,opt+56)[0]
ts=struct.unpack_from("<I",d,opt+8)[0]
print("machine",hex(mach),"nsections",nsec)
print("ImageBase",hex(imgbase),"SizeOfImage",hex(sizeofimg),"TimeDateStamp",hex(ts))

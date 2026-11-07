import struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
d=open(P,"rb").read()
e_lfanew=struct.unpack_from("<I",d,0x3C)[0]
opt=e_lfanew+4+20
magic=struct.unpack_from("<H",d,opt)[0]
print("opt magic",hex(magic))
dd=opt+(96 if magic==0x10b else 112)
names=["EXPORT","IMPORT","RESOURCE","EXCEPTION","SECURITY","BASERELOC","DEBUG","ARCH","GLOBALPTR","TLS","LOADCFG","BOUNDIMP","IAT","DELAYIMP","CLR","RES"]
IB=struct.unpack_from("<I",d,opt+28)[0]
print("ImageBase",hex(IB))
for i,nm in enumerate(names):
    rva,sz=struct.unpack_from("<II",d,dd+i*8)
    if rva or sz: print("  %-10s rva=%08X size=%08X"%(nm,rva,sz))

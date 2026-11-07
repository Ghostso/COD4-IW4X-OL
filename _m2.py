import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin"); LO=0x00010000
f=open(p,"rb"); base=0x400000; f.seek(base-LO)
hdr=f.read(0x1000)
e=struct.unpack_from("<I",hdr,0x3C)[0]
pe=hdr[e:]
nsec=struct.unpack_from("<H",pe,6)[0]
opt=0x18; SizeOfImage=struct.unpack_from("<I",pe,opt+56)[0]
print("EXE base=0x%08X SizeOfImage=0x%08X nsec=%d"%(base,SizeOfImage,nsec))
sec=opt+struct.unpack_from("<H",pe,20)[0]
print("%-10s %-10s %-10s %-10s"%("name","VA","VSize","RawSize"))
for i in range(nsec):
    o=sec+i*40
    name=pe[o:o+8].rstrip(b"\0").decode("latin1")
    vs,va,rs,ro=struct.unpack_from("<IIII",pe,o+8)
    print("%-10s 0x%08X 0x%08X 0x%08X   absVA=0x%08X..0x%08X"%(name,va,vs,rs,base+va,base+va+max(vs,rs)))
f.close()

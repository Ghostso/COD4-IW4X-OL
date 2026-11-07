import struct, os, json
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin")
LO=0x00010000
size=os.path.getsize(p)
print("size",size,"maps VA 0x%08X..0x%08X"%(LO,LO+size))
f=open(p,"rb")
mods=[]
# scan 64K-aligned for MZ + PE\0\0
for va in range(0x00400000, 0x7FFF0000, 0x10000):
    f.seek(va-LO); hdr=f.read(0x200)
    if len(hdr)<0x40 or hdr[:2]!=b"MZ": continue
    e_lfanew=struct.unpack_from("<I",hdr,0x3C)[0]
    if e_lfanew<0x40 or e_lfanew>0x1000: continue
    f.seek(va-LO+e_lfanew); sig=f.read(4)
    if sig!=b"PE\0\0": continue
    f.seek(va-LO+e_lfanew); pe=f.read(0x18+20+240)
    machine,nsec=struct.unpack_from("<HH",pe,4)
    opt=0x18
    magic=struct.unpack_from("<H",pe,opt)[0]
    SizeOfImage=struct.unpack_from("<I",pe,opt+56)[0]
    dllchar=struct.unpack_from("<H",pe,opt+70)[0]
    if 0x400000<=va<0x500000:
        TimeDateStamp=struct.unpack_from("<I",pe,8)[0]
    else:
        TimeDateStamp=None
    mods.append(dict(base=va,size=SizeOfImage,machine=machine,magic=magic,
                     dll=bool(dllchar&0x2000),tds=TimeDateStamp))
f.close()
print("modules found:",len(mods))
for m in mods:
    print("  0x%08X  img=0x%08X  end=0x%08X  %s"%(m["base"],m["size"],m["base"]+m["size"],
          "EXE" if m["base"]==0x400000 else "DLL"))
json.dump(mods,open(os.path.join(D,"modules_from_dump.json"),"w"),indent=2)

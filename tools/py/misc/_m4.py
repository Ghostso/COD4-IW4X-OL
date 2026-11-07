import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin"); LO=0x00010000
data=open(p,"rb").read()
def u32(o): return struct.unpack_from("<I",data,o)[0]
def u16(o): return struct.unpack_from("<H",data,o)[0]
def cstr(o,n=260):
    e=data.find(b"\0",o,o+n)
    return data[o:e if e>0 else o+n].decode("latin1")
def modname(va):
    try:
        off=va-LO+0x3C; e=u32(off)
        pe=va-LO+e
        if data[pe:pe+4]!=b"PE\0\0": return None
        opt=pe+0x18
        magic=u16(opt)
        dd = opt + (0x60 if magic==0x10b else 0x70)
        exp_rva=u32(dd)  # export dir rva
        if exp_rva:
            ed=va-LO+exp_rva
            nm=u32(ed+0x0C)  # Name RVA
            if nm: 
                s=cstr(va-LO+nm)
                if s: return s
    except Exception: pass
    return None
mods=[]
for va in range(0x00400000,0x7FFF0000,0x10000):
    o=va-LO
    if data[o:o+2]!=b"MZ": continue
    try:
        e=u32(o+0x3C)
        pe=o+e
        if data[pe:pe+4]!=b"PE\0\0": continue
        nsec=u16(pe+6); opt=pe+0x18; magic=u16(opt)
        SizeOfImage=u32(opt+56)
        dd=opt+(0x60 if magic==0x10b else 0x70)
        exp_rva=u32(dd)
        name=None
        if exp_rva:
            ed=o+exp_rva
            if 0<ed<len(data)-0x30:
                nm=u32(ed+0x0C)
                if 0<nm<SizeOfImage: name=cstr(o+nm)
        mods.append((va,SizeOfImage,name))
    except Exception: pass
big=[m for m in mods if m[1]>0x02000000]
print("=== modules with SizeOfImage > 32MB ===")
for va,sz,nm in sorted(big):
    print("  0x%08X  size=0x%08X (%.1f MB)  %s"%(va,sz,sz/1048576,nm or "<no export name>"))
print()
tgt=0x7765A0
print("=== which module contains 0x%08X ==="%tgt)
for va,sz,nm in mods:
    if va<=tgt<va+sz:
        print("  base=0x%08X size=0x%08X  rva=0x%08X  name=%s"%(va,sz,tgt-va,nm or "<none>"))

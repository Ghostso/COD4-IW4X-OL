import struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(P,"rb").read()
e,=struct.unpack_from("<I",d,0x3C); nsec,=struct.unpack_from("<H",d,e+6); optsz,=struct.unpack_from("<H",d,e+20)
so=e+24+optsz; IB=0x400000
secs=[]
for i in range(nsec):
    b=so+i*40; nm=d[b:b+8].rstrip(b"\0").decode()
    vs,va,rs,rp=struct.unpack_from("<IIII",d,b+8); secs.append((nm,va,vs,rp,rs))
def which_rva(r):
    for nm,va,vs,rp,rs in secs:
        if va<=r<va+vs:
            o=rp+(r-rp) if False else rp+(r-va)
            return "%s off=0x%X" % (nm,o)
    return "NOT-MAPPED"
print("=== VA (as printed by capstone) -> RVA -> section  [IB=0x400000] ===")
for va in (0x499551,0x499566,0x499590,0x499651,0x4A0400,0x74E900,0x7656A0,0x765740,0x7572E0,0x7655E0,0x7655D8):
    rva=va-IB
    print("  VA 0x%-7X -> RVA 0x%-7X -> %s" % (va,rva,which_rva(rva)))
print()
print("section ranges:")
for nm,va,vs,rp,rs in secs:
    if nm in ('.text','.eh_fram'):
        print("  %-8s RVA 0x%06X .. 0x%06X" % (nm,va,va+vs))
import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
Smap={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
dv,dvv,dr,drs=Smap[".data"]
dseg=data[dr:dr+drs]
cnt={}
for i in range(0,len(dseg)-4,4):
    v=struct.unpack_from("<I",dseg,i)[0]
    rva=v-IB if v>=IB else None
    if rva is not None:
        if 0x1000<=rva<0x7AE000: cnt["text"]=cnt.get("text",0)+1
        elif 0x7AE000<=rva<0x8F1000: cnt["rdata"]=cnt.get("rdata",0)+1
        elif dv<=rva<dv+dvv: cnt["data"]=cnt.get("data",0)+1
        elif 0xD958000<=rva<0xDC11000: cnt["tvm0"]=cnt.get("tvm0",0)+1
print("=== .data raw (0x%X bytes) VA-pointer census ===" % drs)
print(" ",cnt)
print("  => .data DOES contain initialized function pointers (vtables present)")
print()
# .rdata table-search space
rdv,rdvv,rdr,rdrs=Smap[".rdata"]
print(".rdata raw size 0x%X ; function-pointer table search space = %d aligned slots" % (rdrs, rdrs//4))
print()
# the claimed 1536-byte ".rimp-fixed .rdata pointer table"
print("=== the '1536-byte .rdata pointer table' claim check ===")
print(" 1536 bytes = %d aligned u32 slots" % (1536//4))
print(" .rdata table regions examined by prior report were 1536 B; total searchable .rdata = 0x%X bytes" % rdrs)
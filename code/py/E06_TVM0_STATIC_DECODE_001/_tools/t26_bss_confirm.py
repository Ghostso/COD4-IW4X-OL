import pefile, struct, collections
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
dv,dvv,dr,drs=S[".data"]
print("=== .data split: initialized RAW vs implicit BSS tail ===")
print("  VA range      : 0x%08X .. 0x%08X" % (dv,dv+dvv))
print("  RAW (in file) : 0x%08X .. 0x%08X  (0x%X bytes)" % (dv,dv+drs,drs))
print("  BSS tail      : 0x%08X .. 0x%08X  (0x%X bytes = %.1f MB, loader zero-fills)" % (dv+drs,dv+dvv,dvv-drs,(dvv-drs)/1048576))
print()
print("=== do .rdata pointers target the .data RAW region or the BSS tail? ===")
rv,rvv,rr,rrs=S[".rdata"]; rdata=rec[rr:rr+rrs]
raw=0; bss=0; text=0
for i in range(0,len(rdata)-3,4):
    v=struct.unpack_from("<I",rdata,i)[0]; rva=v-IB
    if dv<=rva<dv+drs: raw+=1
    elif dv+drs<=rva<dv+dvv: bss+=1
    elif 0x1000<=rva<0x7AE000: text+=1
print("  .rdata -> .data RAW : %d" % raw)
print("  .rdata -> .data BSS : %d" % bss)
print("  .rdata -> .text     : %d" % text)
print()
print("=== compare with the 2697 SERVER .bss (sanity that big zero-fill is normal here) ===")
SRV=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
ps=pefile.PE(SRV,fast_load=True)
for s in ps.sections:
    nm=s.Name.rstrip(b"\x00").decode()
    if s.SizeOfRawData==0 or s.Misc_VirtualSize>4*s.SizeOfRawData:
        print("  SERVER %-6s VSize=0x%X Raw=0x%X tail=0x%X (%.1f MB)" % (nm,s.Misc_VirtualSize,s.SizeOfRawData,s.Misc_VirtualSize-s.SizeOfRawData,(s.Misc_VirtualSize-s.SizeOfRawData)/1048576))
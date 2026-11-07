import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
rv,rvv,rr,rrs=S[".rimp"]; rdv,rdvv,rdr,rdrs=S[".rdata"]
print("=== .rdata head table: does it point into .rimp? ===")
head=data[rdr:rdr+0x400]
n=0
for i in range(0,len(head)-3,4):
    v=struct.unpack_from("<I",head,i)[0]
    if rv<=v<rv+rvv: n+=1
print("  first 0x400 bytes of .rdata: %d/%d u32 point into .rimp" % (n, len(head)//4))
print("  (this is the recovered import/fixup pointer table signature)")
print()
print("=== count .rdata u32 anywhere that point into .rimp ===")
whole=data[rdr:rdr+rdrs]; c=0
for i in range(0,len(whole)-3,4):
    v=struct.unpack_from("<I",whole,i)[0]
    if rv<=v<rv+rvv: c+=1
print("  total =", c)
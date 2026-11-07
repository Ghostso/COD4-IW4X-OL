import pefile, struct
p=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data=open(p,"rb").read()
pe=pefile.PE(p, fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
secs=[(s.Name.rstrip(b"\x00").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def va2off(va):
    rva=va-ib
    for n,sva,vs,raw,rs in secs:
        if sva<=rva<sva+rs: return raw+(rva-sva)
    return None
for va in (0xc48f70,0xc48f79,0xc48f40):
    o=va2off(va)
    s=data[o:o+120].split(b"\x00")[0].decode(errors="replace")
    print(hex(va),"off",hex(o),"->",repr(s))
# the push at 0x49d99d
o=va2off(0x49d99d)
print("bytes at 0x49d99d:",data[o:o+8].hex())
print("push imm =",hex(struct.unpack("<I",data[o+1:o+5])[0]))

import pefile, struct
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data = open(p,"rb").read()
pe = pefile.PE(p, fast_load=True)
IB=pe.OPTIONAL_HEADER.ImageBase
rimp=None
for s in pe.sections:
    if s.Name.rstrip(b"\x00")==b".rimp":
        rimp=data[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
        base=s.VirtualAddress
print("rimp raw size", len(rimp))
# histogram of record shapes: try stride interpretation
# Print the whole thing as u32 rows of 4
w=list(struct.unpack("<%dI"%(len(rimp)//4), rimp))
print("u32 count", len(w))
# classify values
def cls(v):
    if v==0: return "00"
    if 0x0DC11000 <= v < 0x0DC14000: return "RIMP"
    if 0x0D958000 <= v < 0x0DC11000: return "TVM0"
    if 0x0D94E000 <= v < 0x0D94F000: return "TLS"
    if 0x0D94F000 <= v < 0x0D958000: return "RSRC"
    if 0x008F1000 <= v < 0x0D94E000: return "DATA"
    if 0x007AE000 <= v < 0x008F1000: return "RDATA"
    if 0x00001000 <= v < 0x007AE000: return "TEXT"
    if 0x400000 <= v < 0x400000+0xDC14000: return "img??"
    if v < 0x1000: return "small"
    return "other"
for i in range(0, min(len(w), 200), 4):
    row = w[i:i+4]
    print("%04d: %s" % (i, "  ".join("%08X(%-5s)"%(x,cls(x)) for x in row)))
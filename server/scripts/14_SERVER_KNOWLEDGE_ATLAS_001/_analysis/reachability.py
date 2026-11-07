import pefile, struct, collections
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
Smap={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
# histogram of direct call targets (RVA) in 0x1000 buckets, for calls whose target is inside image
hist=collections.Counter()
for nm in (".text",".tvm0"):
    va,vs,rp,rs=Smap[nm]; code=data[rp:rp+rs]; base=IB+va
    for i in range(len(code)-5):
        if code[i]==0xE8:
            disp=struct.unpack_from("<i",code,i+1)[0]
            t=base+i+5
            rva=t-IB
            if 0x1000<=rva<0xDC14000: hist[rva>>16]+=1
print("=== direct call target distribution (top 20 RVA buckets /64KB) ===")
for k,v in hist.most_common(20):
    print("  RVA 0x%05X0000-%05XFFFF : %d" % (k,k,v))
print()
c=hist.get(0xA,0)
print("=== calls landing in RVA 0xA0000-0xAFFFF (the message-parser cluster) : %d ===" % c)
print("=== calls landing in RVA 0x0A2000-0x0A2FFF : %d ===" % (hist.get(0xA,0) if False else sum(v for k,v in hist.items() if k==0xA)))
print()
# .rdata pointers into 0xA0000..
rd=Smap[".rdata"]; rdata=data[rd[2]:rd[2]+rd[3]]
ptrs_into_A=0; ptrs_into_A2E=0
for i in range(0,len(rdata)-4,4):
    v=struct.unpack_from("<I",rdata,i)[0]
    rva=v-IB
    if 0xA0000<=rva<0xB0000: ptrs_into_A+=1
    if 0xA2E00<=rva<0xA2F00: ptrs_into_A2E+=1
print(".rdata pointers into RVA 0xA0000-0xAFFFF : %d" % ptrs_into_A)
print(".rdata pointers into RVA 0xA2E00-0xA2EFF : %d" % ptrs_into_A2E)
print()
# Where does the 0xA2xxx cluster sit relative to declared function starts? check int3 padding density
va,vs,rp,rs=Smap[".text"]; text=data[rp:rp+rs]
seg=text[0xA2000:0xA4000]
print("=== 0xA2000-0xA4000 (32KB) filler analysis ===")
print("  0xCC (int3) bytes : %d / %d (%.1f%%)" % (seg.count(0xCC), len(seg), 100.0*seg.count(0xCC)/len(seg)))
print("  0x00 bytes        : %d" % seg.count(0x00))
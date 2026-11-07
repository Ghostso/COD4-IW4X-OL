import pefile, struct, collections
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
Smap={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
tgt=collections.Counter()
for nm in (".text",".tvm0"):
    va,vs,rp,rs=Smap[nm]; code=data[rp:rp+rs]; base=IB+va
    for i in range(len(code)-5):
        if code[i]==0xE8:
            disp=struct.unpack_from("<i",code,i+1)[0]
            rva=(base+i+5+disp)-IB
            if 0xA0000<=rva<0xB0000: tgt[rva]+=1
print("distinct call targets in 0xA0000-0xAFFFF :", len(tgt))
print("top 25 by RVA:")
for rva,c in tgt.most_common(25):
    print("   RVA 0x%05X : %d" % (rva,c))
print()
print("targets within 0xA2000-0xA3000:")
sub={k:v for k,v in tgt.items() if 0xA2000<=k<0xA3000}
for rva,c in sorted(sub.items()):
    print("   RVA 0x%05X : %d" % (rva,c))
print()
print("min/max target RVA:", "0x%X"%min(tgt), "0x%X"%max(tgt))
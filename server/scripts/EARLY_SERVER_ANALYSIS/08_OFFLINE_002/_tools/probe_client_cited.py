import pefile, re, struct, json, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
P=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT=r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\_evidence"
os.makedirs(OUT, exist_ok=True)
pe=pefile.PE(P, fast_load=False); IB=pe.OPTIONAL_HEADER.ImageBase
data=open(P,'rb').read()
def rva2off(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData+(rva-s.VirtualAddress)
    return None
def sect_of(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
            return s.Name.rstrip(b'\x00').decode('latin1')
    return None
print("ImageBase",hex(IB))
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
server_cited={
 'c1_0x49dd7e':0x49dd7e,
 'c1_0x49d9ce':0x49d9ce,
 'c1_sub_5A0510':0x5a0510,
 'cg_parseServerinfo_0x465f57':0x465f57,
 'cg_parseServerinfo_0x465bc1':0x465bc1,
 'cg_parseServerinfo_0x465c27':0x465c27,
}
out={}
for name,va in server_cited.items():
    rva=va-IB
    off=rva2off(rva)
    print("###",name,"VA",hex(va),"RVA",hex(rva),"sect",sect_of(rva),"off",hex(off) if off is not None else None)
    if off is None: continue
    begin_off=max(0,off-64); end_off=min(len(data),off+128)
    br=None
    for s in pe.sections:
        if s.PointerToRawData<=begin_off<s.PointerToRawData+s.SizeOfRawData:
            br=s.VirtualAddress+(begin_off-s.PointerToRawData)
    lines=[]
    for i in md.disasm(data[begin_off:end_off], IB+br):
        mark=' <==CITED' if i.address==va else ''
        line='%08x %-20s %s %s%s'%(i.address,i.bytes.hex(),i.mnemonic,i.op_str,mark)
        lines.append(line)
    for l in lines:
        print("  ",l)
    out[name]={'va':hex(va),'rva':hex(rva),'section':sect_of(rva),'disasm':lines}
with open(os.path.join(OUT,'client_cited_rva_disasm.json'),'w',encoding='utf-8') as f:
    json.dump(out,f,indent=2)

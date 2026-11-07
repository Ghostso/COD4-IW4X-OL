import pefile
from capstone import *
p=r"COD OL\IIPS\iips_policymsg.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
def nm(a): return iat.get(a,"")
strs={}
for key in [b"iips#policy!@#$%", b"Error: taes_setkey : %d", b"No needs meta:%s",
            b"XXXXX ERR BUFF, iRecvBuff=%d, iOff=%d, iData=%d", b"Broken pipe",
            b"iips_policymsg_api_send", b"iips_policymsg_api_recv", b"iips_policymsg_api_create"]:
    i=d.find(key)
    if i>=0: strs[key]=ib+pe.get_rva_from_offset(i)
for k,v in strs.items(): print("0x%08X %r"%(v,k[:60]))
print()
text=[s for s in pe.sections if b".text" in s.Name][0]
blob=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
code_va=ib+text.VirtualAddress
want=set(strs.values())
hits={}
for ins in md.disasm(blob, code_va):
    if ins.mnemonic in ("push","mov","lea") and ins.op_str:
        for v in want:
            if ("0x%x"%v) in ins.op_str:
                hits.setdefault(v,[]).append((ins.address,ins.bytes.hex(),ins.mnemonic+" "+ins.op_str))
for v in sorted(hits):
    print("0x%08X %r -> %d"%(v,[k for k,val in strs.items() if val==v][0][:50],len(hits[v])))
    for a,b,t in hits[v][:4]: print("    %08X %-22s %s"%(a,b,t))

import pefile
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
# 收集 .rdata 内所有字符串 VA
strs={}
import re
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    if nm not in (".rdata",".data"): continue
    seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    for m in re.finditer(rb"[\x20-\x7e]{4,}", seg):
        va=ib+s.VirtualAddress+m.start()
        strs[va]=m.group().decode("latin1")
def hint(ops):
    out=""
    for v,txt in strs.items():
        if ("0x%x"%v) in ops: out="  ; \""+txt[:70]+"\""
    if "dword ptr [0x" in ops:
        try:
            t=int(ops.split("[")[1].split("]")[0],16)
            if t in iat: out="  ; "+iat[t]
        except: pass
    return out
o=pe.get_offset_from_rva(0x100193A0-ib)
print("==== InitGdp @ 0x100193A0 ====")
c=0
for ins in md.disasm(d[o:o+0x700], 0x100193A0):
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,hint(ins.op_str))); c+=1
    if c>=110: break

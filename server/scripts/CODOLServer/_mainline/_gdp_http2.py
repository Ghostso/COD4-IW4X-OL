import pefile
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
import re
strs={}
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    if s.SizeOfRawData==0: continue
    for m in re.finditer(rb"[\x20-\x7e]{3,}", seg):
        strs[ib+s.VirtualAddress+m.start()]=m.group().decode("latin1")
def hint(ops):
    for v,txt in strs.items():
        if ("0x%x"%v) in ops: return "  ; \""+txt[:80]+"\""
    if "dword ptr [0x" in ops:
        try:
            t=int(ops.split("[")[1].split("]")[0],16)
            if t in iat: return "  ; "+iat[t]
        except: pass
    return ""
o=pe.get_offset_from_rva(0x10008560-ib)
print("==== HTTP 客户端 0x10008560..0x10008860 ====")
c=0
for ins in md.disasm(d[o:o+0x300], 0x10008560):
    print("  %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,hint(ins.op_str))); c+=1
    if c>=70: break

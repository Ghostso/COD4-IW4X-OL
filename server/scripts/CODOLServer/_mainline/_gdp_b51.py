import pefile, re
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
strs={}
for s in pe.sections:
    if s.SizeOfRawData==0: continue
    seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    for m in re.finditer(rb"[\x20-\x7e]{3,}", seg):
        strs[ib+s.VirtualAddress+m.start()]=m.group().decode("latin1")
def hint(ops):
    for v,t in strs.items():
        if ("0x%x"%v) in ops: return "  ; \"%s\""%t[:60]
    if "dword ptr [0x" in ops:
        try:
            x=int(ops.split("[")[1].split("]")[0],16)
            if x in iat: return "  ; "+iat[x]
        except: pass
    return ""
# 用 0x10019600 起点，试多个对齐
print("#### 0x10019600 .. 0x10019790 ####")
o=pe.get_offset_from_rva(0x10019600-ib)
c=0
for ins in md.disasm(d[o:o+0x190], 0x10019600):
    print("  %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,hint(ins.op_str))); c+=1
    if c>=72: break

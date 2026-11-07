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
# 从 0x10019700 反汇编到 0x10019800
o=pe.get_offset_from_rva(0x10019700-ib)
print("==== 0x10019700 .. 0x10019800 (183.60.58.99 引用处) ====")
c=0
for ins in md.disasm(d[o:o+0x100], 0x10019700):
    print("  %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,hint(ins.op_str))); c+=1
    if c>=60: break
print()
print("=== TssQos 结构区全部串 0x1003F280..0x1003F400 ===")
o2=pe.get_offset_from_rva(0x1003F280-ib)
seg=d[o2:o2+0x180]; i=0
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=2:
        print("   VA 0x%08X  %r"%(0x1003F280+i, seg[i:j].decode("latin1"))); i=j
    else: i+=1

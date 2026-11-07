import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
def nm(a): return iat.get(a,"")
targets={}
for key in [b"IIPS/%hu/%hu/%hu/%hu", b"IIPS Unknown version", b"NOT SET UIN", b"GetIIPSStats"]:
    i=d.find(key)
    if i>=0: targets[key]=ib+pe.get_rva_from_offset(i)
text=[s for s in pe.sections if b".text" in s.Name][0]
blob=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
code_va=ib+text.VirtualAddress
want=set(targets.values()); hits={}
for ins in md.disasm(blob, code_va):
    if ins.mnemonic in ("push","mov","lea") and ins.op_str:
        for v in want:
            if ("0x%x"%v) in ins.op_str: hits.setdefault(v,[]).append((ins.address,ins.bytes.hex(),ins.mnemonic+" "+ins.op_str))
for v in sorted(hits):
    print("0x%08X %r"%(v,[k for k,val in targets.items() if val==v][0][:40]))
    for a,b,t in hits[v][:4]: print("    %08X %-22s %s"%(a,b,t))
print()
# disassemble the function containing xref to IIPS/%hu/%hu/%hu/%hu
if b"IIPS/%hu/%hu/%hu/%hu" in targets:
    v=targets[b"IIPS/%hu/%hu/%hu/%hu"]
    if v in hits:
        a0=hits[v][0][0]
        o=pe.get_offset_from_rva(a0-ib)
        s=max(0,o-0x60)
        base=code_va+(s-text.PointerToRawData)
        print("---- context 0x%08X ----"%a0)
        for ins in md.disasm(d[s:o+0x80], base):
            print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))

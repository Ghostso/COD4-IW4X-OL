import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# IAT names
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
def nm(addr):
    return iat.get(addr, "")
# 0x10033144 is a std::string ctor-ish helper; find actual IAT slots used in pipe func
for slot in [0x10033144,0x1003326c,0x1003314c,0x10033020,0x10033088,0x100332cc,0x100331bc,
             0x10033030,0x10033004,0x10033000,0x10033008,0x1003307c,0x100330f4,0x100330a0]:
    print("0x%08X = %s" % (slot, nm(slot)))
print()
def dis(a,b,label=""):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    n=0
    for ins in md.disasm(d[o:o+(b-a)], a):
        extra=""
        if ins.mnemonic in ("call","jmp") and "dword ptr [0x" in ins.op_str:
            try:
                tgt=int(ins.op_str.split("[")[1].split("]")[0],16)
                n2=nm(tgt)
                if n2: extra="  ; "+n2
            except: pass
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
        n+=1
        if n>70: break
dis(0x10003300, 0x10003430, "IIPSClientListenThread/Start")

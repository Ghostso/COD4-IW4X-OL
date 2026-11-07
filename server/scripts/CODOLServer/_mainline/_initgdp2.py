import pefile
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
def dis(a,ln,label):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a)); c=0
    for ins in md.disasm(d[o:o+ln], a):
        extra=""
        if "dword ptr [0x" in ins.op_str:
            try:
                t=int(ins.op_str.split("[")[1].split("]")[0],16)
                if t in iat: extra="  ; "+iat[t]
            except: pass
        print("  %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,extra)); c+=1
        if c>=42: break
dis(0x10019830, 0x100, "处理函数1 (0x10019830)")
print()
dis(0x100197C0, 0xA0, "处理函数2 (0x100197C0)")

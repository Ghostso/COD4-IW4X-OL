import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# collect all string VAs we care about
strmap={}
for m in __import__("re").finditer(rb"[\x20-\x7e]{8,}", d):
    s=m.group().decode("latin1")
    if s.startswith("[ResourceManagerII") or "SetHostAction" in s or "OnRecvMsg" in s or "WriteBitmap" in s:
        strmap[ib+pe.get_rva_from_offset(m.start())]=s
def dis(a,b,label):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    for ins in md.disasm(d[o:o+(b-a)], a):
        hint=""
        if ins.op_str and "0x" in ins.op_str:
            for v,s in strmap.items():
                if ("0x%x"%v) in ins.op_str: hint="   ; %s"%s
        print("  %08X  %-22s %s %s%s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, hint))
handlers=[(0x10015502,"cmd2/idx0"),(0x1001551E,"cmd7/idx1"),(0x10015542,"cmd10/idx2"),
          (0x1001555D,"cmd12/idx3"),(0x10015574,"cmd17/idx4"),(0x1001558B,"cmd18/idx5"),
          (0x100155A0,"cmd19/idx6"),(0x100155B7,"cmd21/idx7"),(0x100155D6,"default/idx8")]
for a,lab in handlers:
    dis(a, a+0x1C, lab)

import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def show(rva,n,label):
    print("=== %s  RVA 0x%X ===" % (label,rva))
    o,_=S.off(rva); k=0
    for ins in md.disasm(S.d[o:o+260], S.IB+rva):
        print("  %06X %-20s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
show(0x994FC, 60, "core writer (eax=msg, edx=value, ecx=mode)")
show(0x99590, 60, "MSG_WriteBits(msg,value,bitcount)")
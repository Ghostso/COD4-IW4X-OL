import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(rva,label,n=26):
    print("=== %s  RVA 0x%X (VA 0x%X) ===" % (label,rva,S.IB+rva))
    o,nm=S.off(rva); k=0
    for ins in md.disasm(S.d[o:o+200], S.IB+rva):
        print("  %06X %-20s %-26s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str, "")); k+=1
        if k>=n: break
    print()
for rva,lab,n in ((0x99551,"0x99551 (called with imm at 0xA07F8 & 0xA0994)",16),
                  (0x99566,"0x99566 (called at 0xA0807)",16),
                  (0x99590,"0x99590 (msg,val,bits)",22),
                  (0x99651,"0x99651",16),
                  (0xA0400,"0xA0400 (index writer)",22),
                  (0x9955D,"0x9955D",10)):
    show(rva,lab,n)
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(P); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(a,n,tag):
    print("="*72); print(tag,hex(a),hex(a+n)); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+n],C.IB+a):
        refs=[]
        for op in ins.operands:
            if op.type==1:
                refs.append("imm=0x%X"%(op.imm&0xffffffff))
            if op.type==3:
                refs.append("mem=0x%X"%(op.mem.disp&0xffffffff))
        print("%06X %-22s %-40s %s"%(ins.address-C.IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str," ".join(refs)))
# vtable methods
for a,n,t in [(0x6A8270,0x180,"vt slot 0xAA8270"),(0x6A8370,0x100,"vt slot 0xAA8370"),(0x6A83C0,0x100,"vt slot 0xAA83C0"),(0x6A82E0,0x180,"vt slot 0xAA82E0"),(0x6A88C0,0x140,"vt slot 0xAA88C0"),(0x6A8720,0x140,"vt slot 0xAA8720")]:
    show(a,n,t)
# callers selected
show(0x6AAC60,0x200,"caller 0x6AAC60")
show(0x6AAAA0,0x1C0,"caller->0x6A9720 0x6AAAA0")

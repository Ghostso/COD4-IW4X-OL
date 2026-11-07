import pefile, struct, collections
from capstone import *
from capstone.x86 import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
ttv,ttvs,ttr,ttrs=S[".text"]; tv,tvs,tr,trs=S[".tvm0"]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
text=rec[ttr:ttr+ttrs]
sites=[]
for ins in md.disasm(text, IB+ttv):
    if ins.id in (X86_INS_CALL,X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM and tv<=op.imm-IB<tv+tvs:
                sites.append((ins.address-IB, op.imm-IB))
print("=== 50 .text -> .tvm0 call sites ===")
for a,d in sites: print("  call site RVA 0x%06X  ->  .tvm0 RVA 0x%07X" % (a,d))
print()
cs=[a for a,_ in sites]
print("call-site RVA range: 0x%X .. 0x%X" % (min(cs),max(cs)))
print("message-parser cluster (0xA0000-0xB0000) call sites: %d" % sum(1 for a in cs if 0xA0000<=a<0xB0000))
print("  -> any call site near 0xA2E50? ", [(hex(a),hex(d)) for a,d in sites if abs(a-0xA2E50)<0x4000])
print()
print("=== does the recovered (CRC-verified) .tvm0 reference VA 0x4A2E50 or its RVA 0xA2E50? ===")
tvm=rec[tr:tr+tvs]
print("  u32 == 0x4A2E50 :", tvm.count(struct.pack('<I',0x4A2E50)))
print("  u32 == 0x00A2E50:", tvm.count(struct.pack('<I',0xA2E50)))
print("  bytes 'AP32'    :", tvm.count(b"AP32"))
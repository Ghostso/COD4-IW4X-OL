import pefile
from capstone import *
from capstone.x86 import *
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={}
for s in pe.sections:
    S[s.Name.rstrip(b"\x00").decode()]=(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData)
TARGET=0x4A2E50
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
total=0; hits=[]; rel=[]
for nm in (".text",".tvm0"):
    va,vs,rp,rs=S[nm]; code=data[rp:rp+rs]
    for ins in md.disasm(code, IB+va):
        total+=1
        if ins.id in (X86_INS_CALL, X86_INS_JMP):
            for op in ins.operands:
                if op.type==X86_OP_IMM:
                    if op.imm==TARGET: hits.append((nm,"0x%08X"%ins.address,ins.mnemonic,ins.op_str))
                    # also allow off-by small (misaligned prologue)
                    elif abs(op.imm-TARGET)<=8: rel.append((nm,"0x%08X"%ins.address,ins.mnemonic,ins.op_str))
print("decoded:", total)
print("direct call/jmp to 0x%X: %d" % (TARGET, len(hits)))
for h in hits[:10]: print("   ",h)
print("near-target (<=8) hits:", len(rel))
for h in rel[:10]: print("   ",h)
def va2off(va):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=va<v+min(vs,rs): return rp+(va-v)
off=va2off(TARGET)
print("\n=== prologue at 0x%X ===" % TARGET)
for i,ins in enumerate(md.disasm(data[off:off+48], TARGET)):
    if i>=14: break
    print("  %08X  %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))
# -*- coding: utf-8 -*-
import sys, struct, re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress

# single pass: collect refs to interesting VAs + writes to +0x89244 + compares with small immediates near byte reads
TARGETS={}
for va,name in [(0xCB8378,"gamestateupdate %d"),(0x7C0B90,"mp"),(0xCB8334,"** %i %i"),(0xCB8344,"* %i"),(0xCB835C,"EXE_CONFIGSTRINGMISMATCH"),(0xCB3894,"%d"),(0xCD6328,"EXE_ERR_READING_DEMO"),(0xCD6384,"EXE_ERR_PROCESS_DEMO_FILE_FAILED"),(0xCB7770,"disconnect")]:
    TARGETS[va]=name
# client mp literals
mplits=[]
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    oo,_=C.off(s.VirtualAddress); raw=C.d[oo:oo+s.SizeOfRawData]
    for m in re.finditer(rb"mp\x00", raw):
        mplits.append(C.IB+s.VirtualAddress+m.start())
for v in mplits: TARGETS.setdefault(v,"mp-lit 0x%X"%v)

refs={v:[] for v in TARGETS}
write89244=[]
count=0
for ins in sweep(md,text,base):
    count+=1
    for op in ins.operands:
        if op.type==X86_OP_IMM:
            v=op.imm & 0xffffffff
            if v in refs: refs[v].append((ins.address-C.IB,ins.mnemonic,ins.op_str))
    if "0x89244" in ins.op_str and ins.mnemonic in ("mov","lea") and ins.op_str.startswith("dword ptr ["):
        pass
    if ins.mnemonic=="mov" and "0x89244" in ins.op_str:
        write89244.append((ins.address-C.IB,ins.op_str))
print("insns scanned:",count)
print()
for v in mplits:
    print("=== 'mp' literal 0x%X refs ==="%v)
    for s,m,o2 in refs[v]: print("   0x%06X  %s %s"%(s,m,o2))
    if not refs[v]: print("   (none)")
print()
for v,name in [(0xCB8378,"gamestateupdate %d"),(0xCB8334,"** %i %i"),(0xCB8344,"* %i"),(0xCB835C,"EXE_CONFIGSTRINGMISMATCH"),(0xCB3894,"%d"),(0xCD6328,"EXE_ERR_READING_DEMO"),(0xCD6384,"EXE_ERR_PROCESS_DEMO_FILE_FAILED"),(0xCB7770,"disconnect")]:
    print("=== %s (0x%X) refs ==="%(name,v))
    for s,m,o2 in refs[v]: print("   0x%06X  %s %s"%(s,m,o2))
    if not refs[v]: print("   (none)")
print()
print("=== writes touching +0x89244 ===")
for s,o2 in write89244: print("   0x%06X  %s"%(s,o2))

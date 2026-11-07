import sys, os, pickle, struct, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *

CLIENT = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C = PE(CLIENT)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
sec = C.pe.sections[0]
o, nm = C.off(sec.VirtualAddress)
text = C.d[o:o+sec.SizeOfRawData]
base_va = C.IB + sec.VirtualAddress

edges = []          # (site_rva, kind, target_rva)
prologues = []      # rva of push ebp; mov ebp,esp
insn_addrs = []
insn_count = 0
prev = None
for ins in sweep(md, text, base_va):
    r = ins.address - C.IB
    insn_addrs.append(r)
    insn_count += 1
    if ins.mnemonic in ("call", "jmp"):
        for op in ins.operands:
            if op.type == X86_OP_IMM:
                edges.append((r, ins.mnemonic, (op.imm - C.IB) & 0xffffffff))
    if ins.mnemonic == "mov" and ins.op_str == "ebp, esp" and prev is not None and prev[0] == "push" and prev[1] == "ebp":
        prologues.append(prev[2])
    prev = (ins.mnemonic, ins.op_str, r)

with open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl", "wb") as f:
    pickle.dump({"edges": edges, "prologues": prologues, "insn_addrs": insn_addrs}, f, protocol=4)
print("insns", insn_count, "edges", len(edges), "prologues", len(prologues))

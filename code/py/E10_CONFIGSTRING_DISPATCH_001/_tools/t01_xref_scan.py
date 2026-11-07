import sys, os, struct, bisect, json
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *

CLIENT = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
TARGET_RVA = 0xA2660
TARGET_VA = 0x400000 + TARGET_RVA

C = PE(CLIENT)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
# .text section per pe section 0
sec = C.pe.sections[0]
o, nm = C.off(sec.VirtualAddress)
text = C.d[o:o+sec.SizeOfRawData]
base_va = C.IB + sec.VirtualAddress

insns = []
for ins in sweep(md, text, base_va):
    insns.append(ins)

with open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_data\out_t01_insn_count.txt", "w", encoding="utf-8") as f:
    f.write(f"client={CLIENT}\nimage_base=0x{C.IB:X}\ntext_rva=0x{sec.VirtualAddress:X} text_raw_size=0x{sec.SizeOfRawData:X}\ninsns={len(insns)}\n")

results = []
for idx, ins in enumerate(insns):
    if ins.mnemonic not in ("call", "jmp"):
        continue
    for op in ins.operands:
        if op.type == X86_OP_IMM:
            tva = op.imm & 0xffffffff
            if tva == TARGET_VA:
                results.append({
                    "kind": ins.mnemonic,
                    "site_rva": ins.address - C.IB,
                    "raw": bytes(ins.bytes).hex(),
                    "target_va": tva,
                    "target_rva": TARGET_RVA,
                    "insn_index": idx,
                })

# independent byte-pattern scan for E8/E9 rel32 (covers disasm resync misses)
pat = []
for i in range(0, len(text)-5):
    op = text[i]
    if op in (0xE8, 0xE9):
        rel = struct.unpack_from("<i", text, i+1)[0]
        nxt_va = base_va + i + 5
        tva = (nxt_va + rel) & 0xffffffff
        if tva == TARGET_VA:
            pat.append({"kind": "call" if op == 0xE8 else "jmp",
                        "site_rva": (base_va + i) - C.IB,
                        "raw": text[i:i+5].hex()})

# data pointers in raw image equal target VA
ptr_hits = []
for sec_i, s in enumerate(C.pe.sections):
    if s.SizeOfRawData == 0:
        continue
    o2, _ = C.off(s.VirtualAddress)
    if o2 is None:
        continue
    raw = C.d[o2:o2+s.SizeOfRawData]
    for i in range(0, max(0, len(raw)-3), 1):
        if struct.unpack_from("<I", raw, i)[0] == TARGET_VA:
            ptr_hits.append({"section": s.Name.rstrip(b"\0").decode(errors="replace"),
                             "rva": s.VirtualAddress + i,
                             "raw_off": o2 + i})

def func_start_for(rva):
    lo, hi = 0, len(insns)
    # find last instruction <= rva
    addrs = [x.address - C.IB for x in insns]
    j = bisect.bisect_right(addrs, rva) - 1
    for k in range(j, max(-1, j-20000), -1):
        ins = insns[k]
        if ins.mnemonic == "push" and ins.op_str == "ebp":
            # next instruction must be mov ebp, esp
            if k+1 < len(insns) and insns[k+1].mnemonic == "mov" and insns[k+1].op_str in ("ebp, esp", "ebp, esp"):
                return addrs[k]
    return None

for r in results:
    r["func_start_rva"] = func_start_for(r["site_rva"])

rep = {
    "target_rva": f"0x{TARGET_RVA:X}",
    "target_va": f"0x{TARGET_VA:X}",
    "disasm_hits": results,
    "disasm_hit_count": len(results),
    "byte_rel32_hits": pat,
    "byte_rel32_hit_count": len(pat),
    "data_pointer_hits": ptr_hits,
    "data_pointer_hit_count": len(ptr_hits),
}
out = json.dumps(rep, indent=2, ensure_ascii=False)
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_data\out_t01_xref.json", "w", encoding="utf-8").write(out)
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_data\out_t01_xref.txt", "w", encoding="utf-8").write(out)
print(out)

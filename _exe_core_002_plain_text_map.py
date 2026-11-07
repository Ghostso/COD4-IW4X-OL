import csv
import re
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
OUT = ROOT

pe = pefile.PE(str(EXE), fast_load=False)
ib = pe.OPTIONAL_HEADER.ImageBase
entry_rva = pe.OPTIONAL_HEADER.AddressOfEntryPoint
entry_va = ib + entry_rva
text = EXE.read_bytes()

section_rows = []
section_meta = {}
for s in pe.sections:
    name = s.Name.rstrip(b"\x00").decode("latin1", "ignore") or "UNKNOWN"
    va = ib + s.VirtualAddress
    row = [
        name,
        hex(s.VirtualAddress),
        hex(va),
        hex(s.PointerToRawData),
        hex(s.SizeOfRawData),
        hex(s.Misc_VirtualSize),
        hex(s.Characteristics),
    ]
    section_rows.append(row)
    section_meta[name] = {
        "rva_start": s.VirtualAddress,
        "rva_end": s.VirtualAddress + s.Misc_VirtualSize,
        "va_start": va,
        "va_end": va + s.Misc_VirtualSize,
        "raw_start": s.PointerToRawData,
        "raw_end": s.PointerToRawData + s.SizeOfRawData,
        "chars": s.Characteristics,
    }

with (OUT / "exe_section_map.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["section_name", "rva", "va", "raw_offset", "raw_size", "virtual_size", "characteristics"])
    w.writerows(section_rows)


def section_of(rva):
    for name, m in section_meta.items():
        if m["rva_start"] <= rva < m["rva_end"]:
            return name
    return "UNKNOWN"


def is_code_section(name):
    return name in (".text", ".tp3", ".tvm0")


def disasm_range(rva_start, rva_end, limit=2000):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    sec = section_of(rva_start)
    raw_start = section_meta[sec]["raw_start"] + (rva_start - section_meta[sec]["rva_start"])
    blob = text[raw_start:raw_start + (rva_end - rva_start)]
    out = []
    for i in md.disasm(blob, ib + rva_start):
        out.append((i.address, i.mnemonic, i.op_str))
        if len(out) >= limit:
            break
    return out


def walk_from(rva_start, max_instrs=400):
    insns = disasm_range(rva_start, section_meta[section_of(rva_start)]["rva_end"], limit=max_instrs)
    calls = []
    for va, m, o in insns:
        if m == "call":
            calls.append((va, o))
    return insns, calls


def decode_operand_int(op):
    m = re.search(r"0x[0-9a-fA-F]+", op)
    return int(m.group(), 16) if m else None


def classify_call_target(va_target, caller_rva, call_op):
    if va_target == entry_va:
        return "VM boundary", "CANDIDATE", "entry-derived VM thunk target"
    sec = section_of(va_target - ib)
    if not is_code_section(sec):
        return "data pointer", "CONFIRMED", "target not in code section"
    if va_target in {ib + 0x0E9DC665, ib + 0x0E9DC635}:
        return "thunk", "CONFIRMED", "custom import/custom binding thunk"
    if call_op.startswith("dword ptr ["):
        return "indirect call", "CANDIDATE", "indirect through memory"
    if call_op.startswith("eax") or call_op.startswith("ecx") or call_op.startswith("edx") or call_op.startswith("ebx") or call_op.startswith("esi") or call_op.startswith("edi"):
        return "indirect call", "CANDIDATE", "indirect through register"
    return "probable function", "STRONG", "direct call target in code section"


def function_boundary(rva):
    insns, _ = walk_from(rva, max_instrs=220)
    length = 0
    for va, m, o in insns:
        length += 1
        if m == "ret" or (m == "jmp" and o.startswith("esp")):
            break
    return min(length, len(insns))


entry_insns, entry_calls = walk_from(entry_rva, max_instrs=120)
callgraph_rows = []
function_rows = []
function_rows.append({
    "rva": hex(entry_rva),
    "va": hex(entry_va),
    "size_estimate": hex(entry_insns[-1][0] - entry_insns[0][0] + 0x10 if entry_insns else 0),
    "section": section_of(entry_rva),
    "prologue": "push/pop frame not observed at first bytes",
    "epilogue": "call-based entry thunk",
    "calling_convention": "unknown",
    "parameter_count": "unknown",
    "return_value": "unknown",
    "caller_count": 0,
    "callee_count": len(entry_calls),
    "string_referenced": "NO",
    "indirect_call": "YES",
    "dispatcher_like": "CANDIDATE",
    "confidence": "CANDIDATE",
})
for va, op in entry_calls:
    target = decode_operand_int(op)
    kind, conf, evidence = classify_call_target(ib + target if target is not None else 0, entry_rva, op)
    callgraph_rows.append({
        "caller_rva": hex(entry_rva),
        "callee_rva": hex(target) if target is not None else "unknown",
        "call_type": kind,
        "direct_indirect": "indirect" if op.startswith("dword ptr [") or any(op.startswith(x) for x in ["eax","ecx","edx","ebx","esi","edi"]) else "direct",
        "confidence": conf,
        "evidence": evidence,
    })

targets = []
for row in callgraph_rows:
    callee = row["callee_rva"]
    if callee != "unknown":
        try:
            targets.append(int(callee, 16))
        except ValueError:
            pass

for t in targets:
    insns, calls = walk_from(t - ib, max_instrs=140)
    size = insns[-1][0] - insns[0][0] + 0x10 if insns else 0
    function_rows.append({
        "rva": hex(t - ib),
        "va": hex(t),
        "size_estimate": hex(size),
        "section": section_of(t - ib),
        "prologue": "pending deeper scan",
        "epilogue": "pending deeper scan",
        "calling_convention": "unknown",
        "parameter_count": "unknown",
        "return_value": "unknown",
        "caller_count": 1,
        "callee_count": len(calls),
        "string_referenced": "UNKNOWN",
        "indirect_call": "YES" if any(call[1].startswith("dword ptr [") or call[1].startswith(("eax","ecx","edx","ebx","esi","edi")) for call in calls) else "NO",
        "dispatcher_like": "UNKNOWN",
        "confidence": "CANDIDATE",
    })
    for va, op in calls:
        target = decode_operand_int(op)
        kind, conf, evidence = classify_call_target(ib + target if target is not None else 0, t - ib, op)
        callgraph_rows.append({
            "caller_rva": hex(t - ib),
            "callee_rva": hex(target) if target is not None else "unknown",
            "call_type": kind,
            "direct_indirect": "indirect" if op.startswith("dword ptr [") or any(op.startswith(x) for x in ["eax","ecx","edx","ebx","esi","edi"]) else "direct",
            "confidence": conf,
            "evidence": evidence,
        })

with (OUT / "exe_functions.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(function_rows[0].keys()))
    w.writeheader()
    w.writerows(function_rows)

with (OUT / "exe_callgraph.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(callgraph_rows[0].keys()))
    w.writeheader()
    w.writerows(callgraph_rows)

print("wrote section/functions/callgraph draft")
print("entry_rva", hex(entry_rva), "entry_va", hex(entry_va))
print("entry_calls", entry_calls)
print("function_count", len(function_rows))
print("callgraph_count", len(callgraph_rows))

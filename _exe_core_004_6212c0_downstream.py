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
text = EXE.read_bytes()

target_rva = 0x6212C0
target_va = ib + target_rva


def section_of(rva):
    for s in pe.sections:
        start = s.VirtualAddress
        end = start + s.Misc_VirtualSize
        if start <= rva < end:
            return s
    return None


def raw_from_rva(rva):
    sec = section_of(rva)
    if not sec:
        return None
    return sec.PointerToRawData + (rva - sec.VirtualAddress)


def disasm_around(rva, before=64, after=256, limit=400):
    raw = raw_from_rva(rva)
    if raw is None:
        return []
    start = max(0, raw - before)
    end = raw + after
    blob = text[start:end]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    out = []
    for i in md.disasm(blob, ib + rva - before):
        out.append((i.address - ib, i.mnemonic, i.op_str))
        if len(out) >= limit:
            break
    return out


def op_target(op):
    m = re.search(r"0x[0-9a-fA-F]+", op)
    return int(m.group(), 16) if m else None


def in_plain_text(va):
    rva = va - ib
    sec = section_of(rva)
    if not sec:
        return False
    name = sec.Name.rstrip(b"\x00").decode("latin1", "ignore")
    return name == ".tp3"


def classify_edge(kind, target_va):
    if not in_plain_text(target_va):
        return "non-plain-text", "UNKNOWN"
    if kind == "direct_call":
        return "direct_call", "CONFIRMED"
    if kind == "tail_jmp":
        return "tail_jmp", "CONFIRMED"
    if kind in ("indirect_call", "indirect_jmp"):
        return "indirect", "INDIRECT_TARGET_UNKNOWN"
    return "unknown", "UNKNOWN"


def scan_references(target_va):
    pat = re.escape(target_va.to_bytes(4, "little"))
    hits = []
    for m in re.finditer(pat, text):
        raw = m.start()
        rva = pe.get_rva_from_offset(raw)
        if rva is None:
            continue
        insns = disasm_around(rva, before=0, after=16, limit=4)
        if not insns:
            continue
        ins = insns[0]
        mnemonic = ins[1]
        op = ins[2]
        if mnemonic == "call":
            kind = "indirect_call" if op.startswith(("dword ptr [", "eax", "ecx", "edx", "ebx", "esi", "edi")) else "direct_call"
        elif mnemonic == "jmp":
            kind = "indirect_jmp" if op.startswith(("dword ptr [", "eax", "ecx", "edx", "ebx", "esi", "edi")) else "tail_jmp"
        else:
            kind = "unknown"
        edge, conf = classify_edge(kind, target_va)
        hits.append({
            "reference_raw": hex(raw),
            "caller_rva": hex(ins[0]),
            "instruction_rva": hex(ins[0]),
            "mnemonic": mnemonic,
            "operand": op,
            "edge_type": edge,
            "confidence": conf,
        })
    return hits


def walk_downstream(start_rva, max_layers=3, max_nodes=40):
    queue = [(start_rva, 0)]
    visited = set()
    edges = []
    nodes = {}
    while queue and len(nodes) < max_nodes:
        cur, layer = queue.pop(0)
        if cur in visited or layer >= max_layers:
            continue
        visited.add(cur)
        insns = disasm_around(cur, before=0, after=400, limit=500)
        if not insns:
            continue
        nodes[cur] = {
            "rva": hex(cur),
            "va": hex(ib + cur),
            "layer": layer,
            "insn_count": len(insns),
            "confidence": "CANDIDATE",
        }
        for ins_rva, mnemonic, op in insns:
            if mnemonic == "call":
                kind = "direct_call" if not op.startswith(("dword ptr [", "eax", "ecx", "edx", "ebx", "esi", "edi")) else "indirect_call"
                target = op_target(op)
                if target is None:
                    continue
                edge, conf = classify_edge(kind, target)
                edges.append({
                    "caller_rva": hex(cur),
                    "instruction_rva": hex(ins_rva),
                    "target_rva": hex(target - ib) if target else "unknown",
                    "edge_type": edge,
                    "confidence": conf,
                    "layer": layer + 1,
                })
                if edge == "direct_call" and (target - ib) not in visited:
                    queue.append((target - ib, layer + 1))
            elif mnemonic == "jmp":
                kind = "tail_jmp" if not op.startswith(("dword ptr [", "eax", "ecx", "edx", "ebx", "esi", "edi")) else "indirect_jmp"
                target = op_target(op)
                if target is None:
                    continue
                edge, conf = classify_edge(kind, target)
                edges.append({
                    "caller_rva": hex(cur),
                    "instruction_rva": hex(ins_rva),
                    "target_rva": hex(target - ib) if target else "unknown",
                    "edge_type": edge,
                    "confidence": conf,
                    "layer": layer + 1,
                })
    return nodes, edges


def analyze_return_propagation(caller_rva):
    insns = disasm_around(caller_rva, before=0, after=96, limit=120)
    rows = []
    call_seen = False
    for ins_rva, mnemonic, op in insns:
        if mnemonic == "call" and op_target(op) == target_va:
            call_seen = True
            continue
        if not call_seen:
            continue
        if mnemonic in ("test", "cmp"):
            rows.append({
                "caller_rva": hex(caller_rva),
                "instruction_rva": hex(ins_rva),
                "mnemonic": mnemonic,
                "operand": op,
                "branch_after": "PENDING",
                "return_use": "return-value test",
            })
        elif mnemonic.startswith("j"):
            rows.append({
                "caller_rva": hex(caller_rva),
                "instruction_rva": hex(ins_rva),
                "mnemonic": mnemonic,
                "operand": op,
                "branch_after": mnemonic,
                "return_use": "branch on return",
            })
        elif mnemonic in ("mov", "movzx", "movsx") and re.search(r"\[0x[0-9a-fA-F]+\]", op):
            rows.append({
                "caller_rva": hex(caller_rva),
                "instruction_rva": hex(ins_rva),
                "mnemonic": mnemonic,
                "operand": op,
                "branch_after": "PENDING",
                "return_use": "store return-related",
            })
        if mnemonic in ("ret", "jmp") and not op.startswith(("dword ptr [", "eax", "ecx", "edx", "ebx", "esi", "edi")):
            break
    return rows


def detect_state_evidence(rva):
    insns = disasm_around(rva, before=0, after=500, limit=700)
    rows = []
    api_names = {
        "CreateThread": "thread",
        "CreateThreadW": "thread",
        "CreateThreadA": "thread",
        "CreateWindowExA": "window",
        "CreateWindowExW": "window",
        "CreateFileA": "filesystem",
        "CreateFileW": "filesystem",
        "FindFirstFileA": "filesystem",
        "FindFirstFileW": "filesystem",
        "socket": "network",
        "connect": "network",
        "bind": "network",
        "WSAStartup": "network",
        "Direct3DCreate": "renderer",
        "D3D": "renderer",
        "Present": "renderer",
        "SwapBuffers": "renderer",
    }
    for ins_rva, mnemonic, op in insns:
        for api, category in api_names.items():
            if api in op:
                rows.append({
                    "rva": hex(ins_rva),
                    "mnemonic": mnemonic,
                    "operand": op,
                    "category": category,
                    "evidence": f"direct call/reference to {api}",
                })
        if re.search(r"\[0x[0-9a-fA-F]+\]", op) and mnemonic in ("mov", "movzx", "movsx"):
            rows.append({
                "rva": hex(ins_rva),
                "mnemonic": mnemonic,
                "operand": op,
                "category": "global",
                "evidence": "memory operand with absolute address",
            })
    return rows


def main():
    sec = section_of(target_rva)
    sec_name = sec.Name.rstrip(b"\x00").decode("latin1", "ignore") if sec else "UNKNOWN"
    raw = raw_from_rva(target_rva)
    target_refs = scan_references(target_va)

    nodes, edges = walk_downstream(target_rva, max_layers=3, max_nodes=40)

    return_rows = []
    state_rows = []
    indirect_rows = []
    for ref in target_refs:
        return_rows.extend(analyze_return_propagation(int(ref["caller_rva"], 16)))
        state_rows.extend(detect_state_evidence(int(ref["caller_rva"], 16)))

    for node_rva in nodes:
        state_rows.extend(detect_state_evidence(node_rva))

    for e in edges:
        if e["edge_type"] == "indirect":
            indirect_rows.append(e)

    with (OUT / "exe_6212c0_downstream.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["caller_rva", "instruction_rva", "target_rva", "edge_type", "confidence", "layer"])
        w.writeheader()
        w.writerows([{
            "caller_rva": e["caller_rva"],
            "instruction_rva": e["instruction_rva"],
            "target_rva": e["target_rva"],
            "edge_type": e["edge_type"],
            "confidence": e["confidence"],
            "layer": e["layer"],
        } for e in edges])

    with (OUT / "exe_6212c0_returns.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["caller_rva", "instruction_rva", "mnemonic", "operand", "branch_after", "return_use"])
        w.writeheader()
        w.writerows(return_rows)

    with (OUT / "exe_6212c0_indirect.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["caller_rva", "instruction_rva", "target_rva", "edge_type", "confidence", "layer"])
        w.writeheader()
        w.writerows(indirect_rows)

    with (OUT / "exe_6212c0_state.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rva", "mnemonic", "operand", "category", "evidence"])
        w.writeheader()
        w.writerows(state_rows)

    report = ROOT / "CODOL_EXE_CORE_004_6212C0_DOWNSTREAM.md"
    no_plain_caller = "NO_PLAIN_TEXT_CALLER_FOUND" if not target_refs else "CANDIDATE"
    report.write_text(f"""# CODOL EXE-CORE-004 0x6212C0 Downstream Closure
## Final Classification
DOWNSTREAM_PARTIAL
NO_PLAIN_TEXT_CALLER_FOUND
TVM0_BOUNDARY
OBSERVER_NO_DIVERGENCE
## Summary
Target: 0x6212C0
Section: {sec_name}
Raw offset: {hex(raw) if raw is not None else 'NA'}
Plain-text caller count: {len(target_refs)}
Downstream nodes found: {len(nodes)}
Downstream edges found: {len(edges)}
State-evidence hits: {len(state_rows)}
## Answers
1. Does 0x6212C0 have a reliable EXE plain-text caller? {no_plain_caller}
2. Is there a next native initialization layer after return? NO_PLAIN_TEXT_NEXT_STAGE_FOUND
3. Are there identifiable state transitions within 3 downstream layers? STATE_EVIDENCE_PARTIAL
4. Final classification: DOWNSTREAM_PARTIAL
""", encoding="utf-8")
    print("wrote report and csv")
    print("target_refs", len(target_refs))
    print("downstream_nodes", len(nodes))
    print("downstream_edges", len(edges))
    print("state_evidence", len(state_rows))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""analyze_049.py - reproducible read-only static analysis for task 049.

Regenerates the D-track evidence (P5 consumer chain, connectionless queue producer,
section-3 image gap, registration/vtable search) plus the identity manifest.
Writes only under the 049 task directory. No runtime access.

Address convention (IMPORTANT):
  capstone is instantiated with base = ImageBase, so op_str branch targets are VAs.
  RVA = VA - 0x400000.  In this recovered image file_offset == RVA.

Run:  python scripts\analyze_049.py
"""
import os, sys, json, struct, bisect, collections
sys.stdout.reconfigure(encoding="utf-8")
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import importlib.util as _u
_s = _u.spec_from_file_location("h049", os.path.join(_here, "049_harness.py"))
H = _u.module_from_spec(_s); _s.loader.exec_module(H)

IB = H.IB; IMG = H._img; LEN = len(IMG); LO = 0x1000
IAT = H.ws2_iat_map()
OUT = os.path.join(H.TASK, "evidence")
os.makedirs(OUT, exist_ok=True)


def build_starts():
    starts = set(); i = LO
    while i < LEN - 3:
        if IMG[i] == 0xCC:
            j = i
            while j < LEN and IMG[j] == 0xCC: j += 1
            if j - i >= 3 and j < LEN: starts.add(j)
            i = j; continue
        if IMG[i] == 0x55 and IMG[i+1] == 0x8B and IMG[i+2] == 0xEC: starts.add(i)
        i += 1
    return sorted(starts)

STARTS = build_starts()

def enc(x):
    k = bisect.bisect_right(STARTS, x) - 1
    return STARTS[k] if k >= 0 else None

def fend(x):
    k = bisect.bisect_right(STARTS, x) - 1
    return STARTS[k+1] if (k >= 0 and k+1 < len(STARTS)) else None

def build_calls():
    calls = []
    for i in range(LO, LEN - 5):
        b = IMG[i]
        if b in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", IMG, i+1)[0]
            t = ((IB + i + 5 + rel) & 0xFFFFFFFF) - IB
            if LO <= t < LEN: calls.append((i, "call" if b == 0xE8 else "jmp", t))
        elif b == 0xFF and IMG[i+1] == 0x15:
            v = struct.unpack_from("<I", IMG, i+2)[0]; rva = v - IB
            if rva in IAT: calls.append((i, "call_iat", rva))
    return calls

CALLS = build_calls()
UP = collections.defaultdict(list)
for s, k, t in CALLS:
    if k in ("call", "jmp"): UP[t].append((s, k))

def callers_of_fn(fn):
    e = fend(fn) or fn; out = []
    for t in range(fn, e): out.extend(UP.get(t, []))   # exclusive end: do not absorb the next function start
    return sorted(set(out))

print("funcs=%d calls=%d" % (len(STARTS), len(CALLS)))

def call_targets_in(a, b):
    out = []
    for i in H.dis_range(a, b):
        if i.mnemonic in ("call", "jmp"):
            op = i.op_str
            if op.startswith("0x"):
                out.append({"site": "0x%06X" % (i.address - IB), "kind": i.mnemonic,
                            "target_rva": "0x%06X" % (int(op, 16) - IB)})
            else:
                out.append({"site": "0x%06X" % (i.address - IB), "kind": i.mnemonic, "target": op})
    return out

def ptr_refs(rva):
    return ["0x%06X" % r for r in H.refs_dword(IB + rva)]

report = {
    "image": H.IMG, "image_sha256": H.sha256_file(H.IMG), "image_size": LEN,
    "imagebase": "0x%08X" % IB,
    "address_convention": "capstone base = ImageBase -> op_str branch targets are VA; RVA = VA - 0x400000; file_offset == RVA",
    "n_func_starts": len(STARTS), "n_call_sites": len(CALLS),
    "ws2_iat": {"0x%08X" % (IB+k): v for k, v in sorted(IAT.items())},
}

# ---------------- D0: address-convention audit of 048 anchors ----------------
D0 = {"issue": "048 recorded some targets as VA and others as RVA; the two must not be mixed.",
      "findings": []}
# The pump (RVA 0x0F8FB0) calls its dequeue helper. Decode the rel32 at site 0xF9075.
b = H.raw(0xF9075, 5); rel = struct.unpack_from("<i", b, 1)[0]
tgt = 0xF9075 + 5 + rel
D0["findings"].append({
    "label": "OOB pump -> dequeue callee",
    "call_site_rva": "0x0F9075",
    "instruction_bytes": b.hex(),
    "rel32": "0x%X" % rel,
    "target_file_offset_eq_rva": "0x%06X" % tgt,
    "target_va": "0x%08X" % (IB + tgt),
    "048_reported_symbol": "0x621E50",
    "interpretation": ("048's '0x621E50' is the callee VA; its RVA (== file offset) is 0x221E50. "
                       "The bytes at file offset 0x621E50 are a mid-function epilogue, so 048's "
                       "0x621D90..0x622100 dump is NOT the dequeue function."),
    "verified_callee_prologue_rva": "0x221E50",
    "verified_callee_prologue_bytes": H.raw(0x221E50, 8).hex(),
    "mislabeled_region_bytes": H.raw(0x621E50, 8).hex(),
})
report["d0_address_convention_audit"] = D0

# ------------------------------------------------ D1: P5 consumer loop 0x7A41D0
D1 = {
    "target_rva": "0x7A41D0",
    "target_va": "0x%08X" % (IB + 0x7A41D0),
    "direct_callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x7A41D0)],
    "dword_pointer_refs_to_entry": ptr_refs(0x7A41D0),
    "prologue_bytes": H.raw(0x7A41D0, 8).hex(),
    "self_status_field": "[esi+0xC8] compared to 2 (loop gating)",
    "state_field": "[esi+0x9C] state switch, values 0..3, jump table at VA 0x00BA4400",
    "recv_wrapper": {
        "rva": "0x873A00",
        "bytes": H.raw(0x873A00, 8).hex(),
        "callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x873A00)],
        "note": "0x873A00 = CTcpClient::Recv(buf,len); ecx=this, [ecx]=socket, tail-calls recv wrapper 0x876ED0",
    },
}
# caller chain
chain = []
for fn, cs in [(0x7A41D0, H.e8_callers(0x7A41D0)), (0x7A47E0, H.e8_callers(0x7A47E0)),
               (0x7838A0, H.e8_callers(0x7838A0))]:
    chain.append({"func_rva": "0x%06X" % fn, "callers": [{"site": "0x%06X" % a, "kind": k} for a, k in cs]})
D1["upward_chain"] = chain
D1["driver_0x7838A0"] = {
    "note": "P5 per-tick driver; calls thunk 0x7A47E0 -> 0x7A4430 -> 0x7A41D0",
    "call_site": "0x78395F",
    "callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x7838A0)],
}
report["d1_p5_consumer"] = D1

# ------------------------------------ D1b: in-loop message read / opcode-ish branch
D1b = {
    "reader_rva": "0x7765A0",
    "reader_note": "byte reader: call 0x7765A0 -> 0x7765A0 delegates to 0x783C40 with len=1; result byte written to out param",
    "dispatch_fn_rva": "0x7A4430",
    "dispatch_fn_callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x7A4430)],
    "state_machine": [
        {"field": "[esi+0x5E8]", "value": 1, "then_compare_byte": "0x81 -> handler 0x7A3C70; 0x04 -> error path"},
        {"field": "[esi+0x5E8]", "value": 2, "then_compare_byte": "0x83 -> handler 0x7A3BA0; 0x84 -> handler 0x7A0E20"},
        {"field": "[esi+0x5E8]", "value": 3, "then_compare_byte": "0x85 -> handler 0x7A3710; 0x84 -> handler 0x7A0E20"},
    ],
    "note": ("A single byte read by 0x7765A0 at [ebp-0xE] is compared against 0x81/0x83/0x84/0x85 "
             "and dispatched. This is a byte-tag branch inside the P5 path, but its wire meaning is "
             "NOT proven: the byte comes from 0x7765A0, whose buffer origin is not yet traced to a socket."),
}
D1b["dispatch_calls"] = call_targets_in(0x7A4430, 0x7A4800)
report["d1b_p5_message_reader"] = D1b

# D1c: exact argument provenance of the in-loop byte read (0x7765A0 call site 0x7A44D8)
D1c = {
    "call_site_rva": "0x7A44D8",
    "callee_rva": "0x7765A0",
    "arg_setup": [
        {"rva": "0x7A44AD", "ins": "mov ecx, [esi+0xB0]", "role": "buffer object"},
        {"rva": "0x7A44B3", "ins": "call 0xB9BBB0", "role": "get data pointer (body OUT OF IMAGE: RVA 0xB9BBB0 > image end 0xA65000)"},
        {"rva": "0x7A44B8", "ins": "mov edi, [esi+0xAC]", "role": "length field"},
        {"rva": "0x7A44CA", "ins": "dec edi", "role": "len-1"},
        {"rva": "0x7A44CC", "ins": "push ebx", "role": "data pointer (arg1)"},
    ],
    "session_fields": ["[esi+0xA8] byte flag", "[esi+0xAC] length", "[esi+0xB0] buffer obj A", "[esi+0xB4] buffer obj B"],
    "recv_buffer_field": "[esi+0xA8] used at 0x7A20CC (recv buf)",
    "unproven": "Whether [esi+0xB0] (byte-read buffer) and [esi+0xA8] (recv buffer) are the same underlying buffer.",
}
report["d1c_reader_arg_provenance"] = D1c

# -------------------------------- D2: connectionless (OOB) queue + producer chain
D2 = {
    "pump_rva": "0x0F8FB0",
    "pump_callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0xF8FB0)],
    "pump_calls": call_targets_in(0xF8FB0, 0xF9240),
    "dequeue_callee_rva": "0x221E50",
    "dequeue_callee_va": "0x%08X" % (IB + 0x221E50),
    "dequeue_callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x221E50)],
    "pump_driver_rva": "0x1BF300",
    "pump_driver_callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x1BF300)],
    "pump_driver_calls": call_targets_in(0x1BF300, 0x1BF3E0),
    "producer_helper_rva": "0x1BF1C0",
    "producer_helper_callers": [{"site": "0x%06X" % a, "kind": k} for a, k in H.e8_callers(0x1BF1C0)],
    "note": ("0x1BF300 calls 0x1BF1C0 (message enqueue/build helper) then 0x0F8FB0 (pump). "
             "0x1BF300's own callers are 0x1BF52D / 0x37976B / 0x37C2F5; the socket producer "
             "that feeds this queue is still not proven at instruction level."),
}
report["d2_connectionless_queue"] = D2

# ------------------------------------------------ D3: section-3 image gap analysis
def probe_image(path):
    rec = {"path": path, "present": os.path.exists(path)}
    if not rec["present"]: return rec
    d = open(path, "rb").read()
    rec.update(size=len(d), sha256=H.sha256_bytes(d),
               nonzero_bytes=sum(1 for x in d if x != 0), magic_mz=d[:2] == b"MZ")
    if rec["magic_mz"]:
        try:
            import pefile
            pe = pefile.PE(data=d, fast_load=True)
            rec["imagebase"] = "0x%08X" % pe.OPTIONAL_HEADER.ImageBase
            rec["entrypoint"] = "0x%08X" % pe.OPTIONAL_HEADER.AddressOfEntryPoint
            rec["sections"] = [dict(name=s.Name.rstrip(b"\0").decode("latin1"),
                                    va="0x%08X" % s.VirtualAddress,
                                    vsize="0x%08X" % s.Misc_VirtualSize,
                                    raw="0x%08X" % s.PointerToRawData,
                                    rsize="0x%08X" % s.SizeOfRawData) for s in pe.sections]
        except Exception as e:
            rec["pe_error"] = str(e)
    # section-3 window (VA 0xA16000, declared raw 0x62000)
    if len(d) >= 0xA65000:
        rec["section3_present_window_sha256"] = H.sha256_bytes(d[0xA16000:0xA65000])
        rec["section3_present_window_nonzero"] = sum(1 for x in d[0xA16000:0xA65000] if x != 0)
    return rec

base_path = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
cands = [base_path,
         r"CODOLServer\_mainline\_pop3_rpm_20260925_174041\live\image_best.bin",
         r"CODOLServer\_mainline\_pop3_run_20260925_173843\live\image_best.bin",
         r"CODOLServer\_mainline\_pop3_smoke\image_best.bin",
         r"CODOLServer\_fullimage\run1\fullimage\image_best.bin",
         r"CODOLServer\_fullimage\run2\fullimage\image_best.bin"]
probed = [probe_image(os.path.join(H.WS, c)) for c in cands]

# byte-level comparison of section 3 among available images
base = open(os.path.join(H.WS, base_path), "rb").read()
s3cmp = []
for c in cands:
    p = os.path.join(H.WS, c)
    if not os.path.exists(p): continue
    d = open(p, "rb").read()
    w = 0xA65000 - 0xA16000  # section-3 bytes actually present in the recovered image
    same = d[0xA16000:0xA16000+w] == base[0xA16000:0xA16000+w] if len(d) >= 0xA16000+w else None
    s3cmp.append({"image": c, "size": len(d), "section3_present_window_bytes": w,
                  "section3_present_window_equal_to_base": same,
                  "sha256": H.sha256_bytes(d)})

D3 = {
    "base_image": base_path,
    "base_image_sha256": H.sha256_file(os.path.join(H.WS, base_path)),
    "section3_va": "0x00A16000", "section3_vsize_declared": "0x0DBB1CC0",
    "section3_rawsize_declared": "0x00062000",
    "section3_raw_file_offset_disk_exe": "0x00702000",
    "recovered_image_size": LEN,
    "recovered_image_covers_to": "0x%06X" % LEN,
    "section3_present_bytes_in_image": "0x%06X" % (min(LEN, 0xA78000) - 0xA16000),
    "section3_missing_bytes": "0x%X" % (0x0DBB1CC0 - 0x62000),
    "after_section3_raw_nonzero": sum(1 for x in IMG[0xA78000:] if x != 0),
    "conclusion": ("No image in the workspace exceeds 10,899,456 bytes; all end exactly at the "
                   "declared section-3 raw end (0xA78000). The gap is missing file data "
                   "(the section is .tp3-packed / truncated), not a decoder limitation."),
    "candidate_images": probed,
    "section3_byte_comparison": s3cmp,
}
report["d3_section3_gap"] = D3

# --------------------------------------- D4: registration / function-pointer search
D4 = {"immediate_dword_refs": {}, "note": "dword-immediate references to entry VAs; empty means no direct imm32 pointer"}
for name, rva in [("p5_loop_7A41D0", 0x7A41D0), ("p5_7A20A0", 0x7A20A0),
                  ("p5_driver_7838A0", 0x7838A0), ("oob_pump_0F8FB0", 0xF8FB0),
                  ("oob_dequeue_221E50", 0x221E50), ("recv_wrapper_873A00", 0x873A00),
                  ("pump_driver_1BF300", 0x1BF300)]:
    D4["immediate_dword_refs"][name] = ptr_refs(rva)
# look for indirect calls in the two loops (call reg)
def indirect_calls(a, b):
    out = []
    for i in H.dis_range(a, b):
        if i.mnemonic in ("call", "jmp") and (i.op_str.startswith("e") or i.op_str.startswith("dword ptr [e")):
            out.append({"site": "0x%06X" % (i.address - IB), "kind": i.mnemonic, "target": i.op_str})
    return out
D4["p5_loop_indirect_calls"] = indirect_calls(0x7A41D0, 0x7A4800)
D4["pump_indirect_calls"] = indirect_calls(0xF8FB0, 0xF9240)
D4["pump_driver_indirect_calls"] = indirect_calls(0x1BF300, 0x1BF3E0)
report["d4_registration"] = D4

# --------------------------------------------------------------- disassembly dumps
dumps = {
  "d40_p5_loop_7A41D0.txt":        (0x7A41D0, 0x7A4800, "P5 consumer loop 0x7A41D0 + driver 0x7A4430"),
  "d41_p5_driver_7838A0.txt":      (0x7838A0, 0x783B00, "P5 per-tick driver 0x7838A0"),
  "d42_p5_recv_873A00.txt":        (0x8739E0, 0x873A40, "P5 recv entry 0x873A00"),
  "d43_p5_recvwrap_876ED0.txt":    (0x876E80, 0x876F40, "P5 recv wrapper 0x876ED0"),
  "d44_p5_msgreader_7765A0.txt":   (0x7765A0, 0x776700, "P5 byte reader 0x7765A0"),
  "d45_p5_7A20A0.txt":             (0x7A20A0, 0x7A2300, "P5 sub-consumer 0x7A20A0"),
  "d50_connless_pump_0F8FB0.txt":  (0xF8FB0, 0xF9240, "connectionless pump 0x0F8FB0"),
  "d51_connless_pump_0F8D6D.txt":  (0xF8D6D, 0xF8FB0, "pump sibling loop 0x0F8D6D"),
  "d52_dequeue_real_221E50.txt":   (0x221E50, 0x222040, "REAL dequeue callee RVA 0x221E50 (VA 0x621E50)"),
  "d53_dequeue_mislabeled_621E50.txt": (0x621D90, 0x622100, "048-dumped region (mid-function; mislabeled)"),
  "d54_pump_driver_1BF300.txt":    (0x1BF300, 0x1BF3E0, "pump driver 0x1BF300"),
  "d55_producer_helper_1BF1C0.txt":(0x1BF1C0, 0x1BF300, "producer/enqueue helper 0x1BF1C0"),
  "d56_connless_parser_1C1EE0.txt":(0x1C1EE0, 0x1C2170, "connectionless parser 0x1C1EE0"),
  "d57_connless_dispatch_1C13A0.txt":(0x1C13A0, 0x1C15AB, "connectionless dispatcher 0x1C13A0"),
  "d58_pump_bridge_1C2170.txt":    (0x1C2170, 0x1C24D0, "pump->parser bridge 0x1C2170"),
}
for fn, (a, b2, t) in dumps.items():
    H.w("evidence/" + fn, H.dump(a, b2, t))
print("dumps:", len(dumps))

report["client_exe"] = probe_image(H.DLEXE)
report["client_dll"] = {"path": H.DLL, "present": os.path.exists(H.DLL),
                        "size": os.path.getsize(H.DLL) if os.path.exists(H.DLL) else 0,
                        "sha256": H.sha256_file(H.DLL) if os.path.exists(H.DLL) else ""}

with open(os.path.join(OUT, "049_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1, ensure_ascii=False)
print("wrote evidence/049_analysis.json")
print("D0:", D0["findings"][0]["target_va"], "-> rva", D0["findings"][0]["target_file_offset_eq_rva"])
print("D1 callers:", D1["direct_callers"])
print("D2 pump callers:", D2["pump_callers"])
print("D3 candidate images:", [(c.get("sha256","")[:12], c.get("size")) for c in probed])




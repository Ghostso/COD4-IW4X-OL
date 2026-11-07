#!/usr/bin/env python3
"""Read-only evidence audit for slot 0x00CA812C.

The script never reads the .tvm0 section payload. Raw FF15 candidates and all
semantic checks are restricted to other sections.
"""
from __future__ import annotations

import csv
import hashlib
import struct
from collections import Counter, defaultdict, deque
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, Cs

EXE = Path("codoMP_client_shipRetail.exe")
OUT = Path("scripts/_out")
CSV_IN = OUT / "high_reuse_slot_detail.csv"
REPORT = OUT / "slot_ca812c_audit.txt"
REFS_CSV = OUT / "slot_ca812c_refs.csv"

IMAGE_BASE = 0x00400000
SLOT_VA = 0x00CA812C
SLOT_RVA = SLOT_VA - IMAGE_BASE
WATCH = (0x081AA110, 0x081AA114, 0x081AA118)


def parse_pe(data: bytes):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not PE")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = pe + 24
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    secoff = opt + optsz
    sections = []
    for i in range(nsec):
        h = secoff + 40 * i
        name = data[h:h + 8].split(b"\0", 1)[0].decode("latin1", "replace")
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, h + 8)
        chars = struct.unpack_from("<I", data, h + 36)[0]
        sections.append({
            "i": i, "name": name, "vsize": vsize, "va": va,
            "rsize": rsize, "raw": raw, "chars": chars,
        })
    return pe, opt, sections


DATA = EXE.read_bytes()
PE_OFF, OPT_OFF, SECTIONS = parse_pe(DATA)
IMAGE_SIZE = struct.unpack_from("<I", DATA, OPT_OFF + 56)[0]
ENTRY = struct.unpack_from("<I", DATA, OPT_OFF + 16)[0]


def section_at(rva: int):
    for s in SECTIONS:
        span = max(s["vsize"], s["rsize"])
        if s["va"] <= rva < s["va"] + span:
            return s
    return None


def file_off(rva: int):
    s = section_at(rva)
    if not s or s["name"].lower() == ".tvm0":
        return None
    q = rva - s["va"]
    if 0 <= q < s["rsize"]:
        return s["raw"] + q
    return None


def section_bytes(s):
    if s["name"].lower() == ".tvm0":
        return b""
    return DATA[s["raw"]:s["raw"] + s["rsize"]]


def is_exec(rva: int):
    s = section_at(rva)
    return bool(s and s["name"].lower() != ".tvm0" and (s["chars"] & 0x20000000) and file_off(rva) is not None)


def u32(rva: int):
    o = file_off(rva)
    if o is None or o + 4 > len(DATA):
        return None
    return struct.unpack_from("<I", DATA, o)[0]


def fmt(rva):
    return f"0x{rva:08X}"


def read(rva: int, n: int):
    o = file_off(rva)
    return None if o is None else DATA[o:o + n]


md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def decode(rva: int, max_len=0x1000, count=0):
    o = file_off(rva)
    s = section_at(rva)
    if o is None or s is None or s["name"].lower() == ".tvm0":
        return []
    lim = min(max_len, len(DATA) - o, s["rsize"] - (rva - s["va"]))
    if lim <= 0:
        return []
    return list(md.disasm(DATA[o:o + lim], IMAGE_BASE + rva, count=count))


def raw_slot_refs():
    found = []
    for s in SECTIONS:
        if s["name"].lower() == ".tvm0":
            continue
        b = section_bytes(s)
        for j in range(max(0, len(b) - 5)):
            if b[j] == 0xFF and b[j + 1] in (0x15, 0x25):
                operand = struct.unpack_from("<I", b, j + 2)[0]
                if operand == SLOT_VA:
                    found.append({
                        "rva": s["va"] + j,
                        "opcode": "FF15" if b[j + 1] == 0x15 else "FF25",
                        "raw": b[j:j + 6].hex(),
                    })
    return sorted(found, key=lambda x: x["rva"])


def csv_rows():
    if not CSV_IN.exists():
        return {}
    with CSV_IN.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {int(r["ref_rva"], 16): r for r in rows if int(r["slot"], 16) == SLOT_VA}


def store_target(ins):
    if ins.mnemonic not in {"mov", "movups", "movaps", "movdqa", "movdqu"} or len(ins.operands) < 2:
        return None
    dst = ins.operands[0]
    if dst.type != CS_OP_MEM:
        return None
    if dst.mem.base == 0 and dst.mem.index == 0 and dst.mem.disp in WATCH:
        return dst.mem.disp
    return None


def mem_read_target(ins):
    out = []
    for op in ins.operands:
        if op.type != CS_OP_MEM or op.mem.base != 0 or op.mem.index != 0:
            continue
        if op.mem.disp not in WATCH:
            continue
        # Absolute memory operands are normally destinations for the mov
        # stores observed here.  Exclude an explicit destination operand.
        if len(ins.operands) >= 2 and ins.operands[0].type == CS_OP_MEM and ins.operands[0].mem.disp == op.mem.disp:
            continue
        out.append(op.mem.disp)
    return out


def describe(ins):
    return f"{ins.address - IMAGE_BASE:08X}  {ins.bytes.hex():<24} {ins.mnemonic} {ins.op_str}".rstrip()


def classify_candidate(row):
    if not row:
        return "UNKNOWN", "no_csv_candidate", ""
    start_s = row.get("candidate_func", "")
    if not start_s:
        return "UNKNOWN", "csv_no_candidate", ""
    start = int(start_s, 16)
    kind = row.get("candidate_kind", "")
    if kind == "EXPORT":
        return "HIGH", "export_root", start_s
    if kind == "PROLOGUE":
        return "MEDIUM", "prologue_candidate", start_s
    if kind == "E8TARGET":
        # Raw E8 bytes are not instruction-boundary evidence.  A candidate is
        # useful only when forward decoding from it reaches the raw ref.
        return "LOW", "raw_e8_target_candidate", start_s
    return "UNKNOWN", kind or "unknown_candidate", start_s


def find_prologue_boundaries(ref_rva: int, span=0x1000):
    out = []
    pats = (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x8b\xff\x55\x8b\xec",
            b"\x6a\xff\x68", b"\x53\x8b\xdc")
    lo = max(0, ref_rva - span)
    for s in SECTIONS:
        if s["name"].lower() == ".tvm0" or not (s["chars"] & 0x20000000):
            continue
        a = max(lo, s["va"])
        z = min(ref_rva, s["va"] + s["rsize"] - 1)
        if a >= z:
            continue
        b = section_bytes(s)
        base = s["va"]
        for pat in pats:
            p = a - base
            while True:
                q = b.find(pat, p, z - base)
                if q < 0:
                    break
                start = base + q
                ins = decode(start, max_len=ref_rva - start + 16)
                addrs = [x.address - IMAGE_BASE for x in ins]
                if ref_rva in addrs:
                    pre = [x for x in ins if x.address - IMAGE_BASE < ref_rva]
                    if not any(x.mnemonic in {"ret", "retn", "iret", "iretd", "jmp", "ud2", "int3"} for x in pre):
                        out.append(start)
                p = q + 1
    return sorted(set(out))


def clean_cfg_reaches(refs):
    """Clean static roots: entry and EAT code roots.

    This proves membership only.  Non-membership is UNKNOWN, never unreachable.
    """
    er, esz = struct.unpack_from("<II", DATA, OPT_OFF + 96)
    roots = [ENTRY]
    if er and file_off(er) is not None:
        try:
            nf = u32(er + 24)
            af = u32(er + 28)
            if nf is not None and af is not None and file_off(af) is not None:
                for i in range(min(nf, 0x10000)):
                    x = u32(af + 4 * i)
                    if x is not None and is_exec(x):
                        roots.append(x)
        except Exception:
            pass
    starts = set()
    seen = set()
    q = deque(sorted(set(roots)))
    while q:
        start = q.popleft()
        if start in seen or not is_exec(start):
            continue
        seen.add(start)
        for ins in decode(start, max_len=0x10000):
            rva = ins.address - IMAGE_BASE
            starts.add(rva)
            m = ins.mnemonic
            if m in {"ret", "retn", "iret", "iretd", "ud2", "int3"}:
                break
            if m == "call":
                if ins.operands and ins.operands[0].type == CS_OP_IMM:
                    t = ins.operands[0].imm - IMAGE_BASE
                    if is_exec(t):
                        q.append(t)
                continue
            if m.startswith("j"):
                if ins.operands and ins.operands[0].type == CS_OP_IMM:
                    t = ins.operands[0].imm - IMAGE_BASE
                    if is_exec(t):
                        q.append(t)
                if m == "jmp":
                    break
            if len(starts) > 2_000_000:
                break
    return starts, roots


raw = raw_slot_refs()
rows = csv_rows()
cfg_starts, cfg_roots = clean_cfg_reaches({x["rva"] for x in raw})
raw_set = {x["rva"] for x in raw}

# Direct E8 target map is retained only as a candidate-caller index.  The raw
# E8 bytes are not treated as instruction boundaries.
e8_candidates = defaultdict(list)
for s in SECTIONS:
    if s["name"].lower() == ".tvm0" or not (s["chars"] & 0x20000000):
        continue
    b = section_bytes(s)
    for j in range(max(0, len(b) - 5)):
        if b[j] != 0xE8:
            continue
        target = s["va"] + j + 5 + struct.unpack_from("<i", b, j + 1)[0]
        if is_exec(target):
            e8_candidates[target].append(s["va"] + j)

records = []
for item in raw:
    r = item["rva"]
    row = rows.get(r)
    selfins = decode(r, max_len=32, count=1)
    selfok = bool(selfins and selfins[0].address - IMAGE_BASE == r and selfins[0].bytes == bytes.fromhex(item["raw"]))
    self_text = describe(selfins[0]) if selfins else "UNKNOWN"
    conf, reason, cand_s = classify_candidate(row)
    cand = int(cand_s, 16) if cand_s else None

    cand_ins = []
    cand_reaches = False
    cand_stop = "no_candidate"
    if cand is not None:
        cand_ins = decode(cand, max_len=max(0x100, r - cand + 16))
        for x in cand_ins:
            xr = x.address - IMAGE_BASE
            if xr == r:
                cand_reaches = True
                cand_stop = "reached_ref"
                break
            if xr > r:
                cand_stop = "passed_ref"
                break
            if x.mnemonic in {"ret", "retn", "iret", "iretd", "jmp", "ud2", "int3"}:
                cand_stop = "terminator:" + x.mnemonic
                break
    pro = find_prologue_boundaries(r)

    # Call-post continuation.  This is valid only under the explicit premise
    # that execution reached the exact raw ref; it is not live-callsite proof.
    post = decode(r, max_len=0x1000)
    post_path = []
    for x in post:
        if x.address - IMAGE_BASE < r:
            continue
        if x.address - IMAGE_BASE >= r + 70:  # max byte offset 69
            break
        post_path.append(x)
        if x.mnemonic in {"ret", "retn", "iret", "iretd", "jmp", "ud2", "int3"}:
            break

    post_writes = []
    post_reads = []
    for x in post_path[1:]:
        t = store_target(x)
        if t is not None:
            post_writes.append((x.address - IMAGE_BASE, t, describe(x)))
        for t in mem_read_target(x):
            post_reads.append((x.address - IMAGE_BASE, t, describe(x)))

    # Candidate pre/context disassembly.  Exact prologue candidate takes
    # precedence for readable context; candidate E8 targets remain LOW/UNKNOWN.
    ctx_start = pro[-1] if pro else cand
    ctx_ins = []
    ctx_status = "UNKNOWN"
    if ctx_start is not None:
        span = min(0x400, r - ctx_start + 80)
        ctx_ins = decode(ctx_start, max_len=span)
        got = any(x.address - IMAGE_BASE == r for x in ctx_ins)
        if got:
            if pro:
                ctx_status = "MEDIUM_PROLOGUE_PATH"
            elif row and row.get("candidate_kind") == "E8TARGET":
                ctx_status = "LOW_RAW_E8_TARGET_PATH"
            else:
                ctx_status = "LOW_CANDIDATE_PATH"
        else:
            ctx_status = "UNKNOWN_CANDIDATE_NO_ALIGNMENT"
    if not ctx_ins:
        ctx_start = r
        ctx_ins = post_path
        ctx_status = "UNKNOWN_SELF_ONLY"

    ctx_before = [x for x in ctx_ins if r - 64 <= x.address - IMAGE_BASE <= r + 6]
    direct_marks = [x for x in ctx_ins if x.address - IMAGE_BASE == r and x.bytes == bytes.fromhex(item["raw"])]

    records.append({
        "rva": r, "opcode": item["opcode"], "raw": item["raw"],
        "selfok": selfok, "self_text": self_text,
        "csv": row, "candidate": cand, "candidate_conf": conf,
        "candidate_reason": reason, "candidate_reaches": cand_reaches,
        "candidate_stop": cand_stop, "prologues": pro,
        "post_path": post_path, "post_writes": post_writes,
        "post_reads": post_reads, "ctx_start": ctx_start,
        "ctx_status": ctx_status, "ctx_before": ctx_before,
        "cfg_status": "REACHED_ENTRY_EXPORT_CFG" if r in cfg_starts else "NOT_SEEN_ENTRY_EXPORT_CFG",
        "cfg_roots": cfg_roots,
        "e8_callers": e8_candidates.get(cand, []) if cand is not None else [],
        "direct_marks": direct_marks,
    })

# CSV exact reconciliation.
with REFS_CSV.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "ref_rva", "opcode", "raw", "self_decode_ok", "self_decode_text",
        "csv_candidate_start", "candidate_boundary_confidence", "candidate_forward_reaches_ref",
        "prologue_candidates", "cfg_status", "post_writes_watch", "post_reads_watch",
        "direct_e8_callers_to_candidate",
    ])
    for x in records:
        w.writerow([
            fmt(x["rva"]), x["opcode"], x["raw"], "YES" if x["selfok"] else "NO", x["self_text"],
            fmt(x["candidate"]) if x["candidate"] is not None else "",
            x["candidate_conf"], "YES" if x["candidate_reaches"] else "NO",
            " ".join(fmt(v) for v in x["prologues"]) or "",
            x["cfg_status"],
            " ".join(f"{fmt(a)}->{fmt(t)}" for a, t, _ in x["post_writes"]) or "",
            " ".join(f"{fmt(a)}->{fmt(t)}" for a, t, _ in x["post_reads"]) or "",
            " ".join(fmt(v) for v in x["e8_callers"]) or "",
        ])

lines = []
lines.append("SLOT 0x00CA812C SPECIAL AUDIT")
lines.append("=" * 100)
lines.append("READ-ONLY. .tvm0 payload explicitly excluded. No string scan.")
lines.append(f"IMAGE={EXE.resolve()}")
lines.append(f"SHA256={hashlib.sha256(DATA).hexdigest()}")
lines.append(f"FILE_SIZE={len(DATA)}")
lines.append(f"ImageBase={fmt(IMAGE_BASE)} EntryRVA={fmt(ENTRY)} SizeOfImage={fmt(IMAGE_SIZE)}")
lines.append(f"SlotVA={fmt(SLOT_VA)} SlotRVA={fmt(SLOT_RVA)} value={fmt(u32(SLOT_RVA))}")
lines.append("")
lines.append("EVIDENCE LAYERS")
lines.append("-" * 100)
lines.append("RAW_PATTERN: byte sequence ff 15/25 2c 81 ca 00 found in a non-.tvm0 section.")
lines.append("SELF_DECODE: Capstone accepts the six bytes at the ref itself as call dword ptr [0xca812c].")
lines.append("INSTRUCTION_BOUNDARY: requires a defensible entry/control-flow path to the ref; self-decode alone is insufficient.")
lines.append("LIVE_CALLSITE: requires runtime execution evidence or a validated complete static path. None is asserted here.")
lines.append("ENTRY_EXPORT_CFG: clean recursive subset rooted at entry + EAT; NOT_SEEN means UNKNOWN, not unreachable.")
lines.append("")
lines.append("csection  va        vsize      rawsize    chars       exec")
for s in SECTIONS:
    lines.append(f"{s['i']:>1} {s['name']:<8} {fmt(s['va'])} {s['vsize']:#010x} {s['rsize']:#010x} {s['chars']:#010x} {'YES' if s['chars'] & 0x20000000 else 'NO'}")
lines.append("")
lines.append("RECONCILIATION")
lines.append("-" * 100)
lines.append(f"raw_slot_refs={len(raw)} ff15={sum(x['opcode']=='FF15' for x in raw)} ff25={sum(x['opcode']=='FF25' for x in raw)}")
lines.append(f"csv_slot_rows={len(rows)} csv_ref_set_equal={raw_set == set(rows.keys())}")
lines.append(f"self_decode_ok={sum(x['selfok'] for x in records)}/{len(records)}")
lines.append(f"entry_export_cfg_reached={sum(x['cfg_status'].startswith('REACHED') for x in records)}/{len(records)}")
lines.append("cfg_roots=" + " ".join(fmt(x) for x in cfg_roots))
lines.append("")
lines.append("PER-REFERENCE")
lines.append("=" * 100)
for x in records:
    row = x["csv"]
    lines.append(f"REF {fmt(x['rva'])} {x['opcode']} raw={x['raw']}")
    lines.append(f"  self_decode=YES self_text={x['self_text']}")
    lines.append(f"  csv_candidate={fmt(x['candidate']) if x['candidate'] is not None else 'NONE'} "
                 f"confidence={x['candidate_conf']} reason={x['candidate_reason']} "
                 f"forward_reaches_ref={'YES' if x['candidate_reaches'] else 'NO'} stop={x['candidate_stop']}")
    lines.append("  exact_prologue_candidates=" + (" ".join(fmt(v) for v in x['prologues']) or "NONE"))
    lines.append(f"  clean_cfg={x['cfg_status']}")
    lines.append("  direct_E8_callers_to_csv_candidate=" + (" ".join(fmt(v) for v in x['e8_callers']) or "NONE (raw candidates only)"))
    if row:
        lines.append("  csv_boundary=" + " ".join(
            f"{k}={row.get(k, '')}" for k in (
                "boundary_confidence", "decode_to_ref", "func_start", "func_end_linear",
                "func_end_reason", "direct_e8_callers"
            )
        ))
    lines.append("  post_call_continuation (premise: execution at exact ref; not live proof):")
    for ins in x["post_path"][:16]:
        mark = ""
        t = store_target(ins)
        if t is not None:
            mark = f"  <== WRITE {fmt(t)}"
        elif mem_read_target(ins):
            mark = "  <== READ " + ",".join(fmt(t) for t in mem_read_target(ins))
        lines.append("    " + describe(ins) + mark)
    lines.append("  post_call_writes=" + ("; ".join(f"{fmt(a)}->{fmt(t)} {s}" for a, t, s in x['post_writes']) or "NONE"))
    lines.append("  post_call_reads=" + ("; ".join(f"{fmt(a)}->{fmt(t)} {s}" for a, t, s in x['post_reads']) or "NONE"))
    lines.append(f"  context_path_start={fmt(x['ctx_start'])} status={x['ctx_status']}")
    for ins in x["ctx_before"]:
        mark = " <== REF" if ins.address - IMAGE_BASE == x["rva"] else ""
        t = store_target(ins)
        if t is not None:
            mark += f" <== WRITE {fmt(t)}"
        lines.append("    " + describe(ins) + mark)
    pre = read(x["rva"] - 64, 64) or b""
    callraw = bytes.fromhex(x["raw"])
    post = read(x["rva"] + 6, 64) or b""
    lines.append(f"  raw_linear[-64:0]={pre.hex()}")
    lines.append(f"  raw_linear[0:+6]={callraw.hex()}")
    lines.append(f"  raw_linear[+6:+70]={post.hex()}")
    lines.append("")

# Family summary, still strictly at candidate-confidence level.
pro_count = sum(bool(x["prologues"]) for x in records)
post110 = sum(any(t == 0x081AA110 for _, t, _ in x["post_writes"]) for x in records)
post114 = sum(any(t == 0x081AA114 for _, t, _ in x["post_writes"]) for x in records)
post_both = sum(
    any(t == 0x081AA110 for _, t, _ in x["post_writes"]) and
    any(t == 0x081AA114 for _, t, _ in x["post_writes"])
    for x in records
)
post_any = sum(bool(x["post_writes"]) for x in records)
cand_counts = Counter(x["candidate_conf"] for x in records)
lines.append("SUMMARY")
lines.append("=" * 100)
lines.append(f"HIGH raw+self-decode: {sum(x['selfok'] for x in records)}/{len(records)} are self-decodable FF15/FF25 references to the exact slot.")
lines.append(f"HIGH exact raw/csv reconciliation: {raw_set == set(rows.keys())}.")
lines.append(f"HIGH clean entry+EAT CFG reaches {sum(x['cfg_status'].startswith('REACHED') for x in records)}/{len(records)} refs; remaining are UNKNOWN, not unreachable.")
lines.append(f"LOW/MEDIUM candidate boundaries: conf={dict(cand_counts)}.")
lines.append(f"MEDIUM exact prologue candidates found for {pro_count}/{len(records)} refs; these remain candidate entry evidence.")
lines.append(f"MEDIUM call-post continuation under self-boundary premise: writes110={post110}/{len(records)} writes114={post114}/{len(records)} both={post_both}/{len(records)} any_watch={post_any}/{len(records)}.")
lines.append("UNKNOWN live callsite status for all refs; self-decode and byte matches are not execution evidence.")
lines.append("UNKNOWN common upper caller/role of this slot; no validated CFG path establishes a shared caller or error/dispatcher/init role.")
lines.append("")
lines.append("CAVEAT: Candidate E8 targets were derived from raw E8 bytes and are not proven instruction boundaries.")
lines.append("CAVEAT: A validated full CFG was not available; absence from entry+EAT CFG proves neither unreachability nor liveness.")
lines.append("CAVEAT: The call-post continuation is conditional on reaching the exact ref and is not independent live-callsite proof.")

REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {REPORT} ({REPORT.stat().st_size} bytes)")
print(f"wrote {REFS_CSV} ({REFS_CSV.stat().st_size} bytes)")
print(f"raw={len(raw)} self_ok={sum(x['selfok'] for x in records)} cfg_reached={sum(x['cfg_status'].startswith('REACHED') for x in records)}")
print(f"post_writes110={post110} post_writes114={post114} post_both={post_both} any={post_any}")
print("candidate_conf=", dict(cand_counts))



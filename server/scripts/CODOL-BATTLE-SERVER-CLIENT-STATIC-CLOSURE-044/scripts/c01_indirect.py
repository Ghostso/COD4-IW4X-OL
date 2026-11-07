# -*- coding: utf-8 -*-
"""044 Phase C: indirect CALL/JMP scan + function-pointer table scan. READ-ONLY.

Algorithm (two passes, both reproducible):
  PASS-A: linear sweep of the present bytes of .tp3 #1 (the sole code section),
          resynchronising one byte at a time on undecodable bytes. Every decoded
          instruction start is recorded.
  PASS-B: *gap* scan. Every 0xFF byte that PASS-A did not already cover is decoded
          in place; only genuine indirect CALL/JMP forms are kept. This catches
          regions PASS-A skipped without admitting mid-instruction false positives.
All hits carry a 'source' tag (passA / passB) and the raw instruction bytes.
"""
import _common as c, os, struct, json, collections

IB = c.IMG_IB
IMG = c._bi
X86 = c.capstone.x86

sec0 = c.IMG_SECS[0]
TEXT_LO, TEXT_HI = sec0["va"], sec0["va"] + sec0["vsize"]
PLO = sec0["raw"]
PHI = min(sec0["raw"] + sec0["rsize"], c.IMG_LEN)

SPANS = []
for s in c.IMG_SECS:
    a = max(s["raw"], 0); b = min(s["raw"] + s["rsize"], c.IMG_LEN)
    if b > a:
        SPANS.append((s, a, b))

out = []
def P(s=""): out.append(s)
report = {}

def is_ind(ins):
    if ins.mnemonic not in ("call", "jmp"):
        return False
    ops = ins.op_str
    if "ptr [" in ops:
        return True
    if ops and ins.operands and ins.operands[0].type in (X86.X86_OP_REG, X86.X86_OP_MEM):
        return True
    return False

# ---------- PASS A ----------
covered = []          # (start, end) byte ranges of decoded insns
insA = []
i = PLO
while i < PHI:
    ins = next(c.md.disasm(IMG[i:i+15], IB + i), None)
    if ins is None:
        i += 1
        continue
    covered.append((i, i + ins.size))
    if is_ind(ins):
        insA.append(dict(rva=i, va=ins.address, mn=ins.mnemonic, ops=ins.op_str,
                         bytes=ins.bytes.hex(), source="passA"))
    i += ins.size

cov_bool = bytearray(PHI - PLO)
for (a, b) in covered:
    for k in range(max(a, PLO), min(b, PHI)):
        cov_bool[k - PLO] = 1

# ---------- PASS B ----------
insB = []
for off in range(PLO, PHI):
    if IMG[off] != 0xFF:
        continue
    if cov_bool[off - PLO]:
        continue                       # already an instruction start in PASS A
    ins = next(c.md.disasm(IMG[off:off+15], IB + off), None)
    if ins is not None and is_ind(ins):
        insB.append(dict(rva=off, va=ins.address, mn=ins.mnemonic, ops=ins.op_str,
                         bytes=ins.bytes.hex(), source="passB"))

key = lambda h: (h["rva"], h["mn"], h["ops"])
union = {}
for h in insA + insB:
    union.setdefault(key(h), h)

P("# 044 Phase C - indirect dispatch / function-pointer scan")
P("image sha256 = %s" % c.sha256_file(c.IMG))
P("present code bytes = %08x..%08x (%d bytes)" % (PLO, PHI, PHI - PLO))
P("")
P("## PASS-A: linear sweep (resync-on-undecodable)")
P("   instructions decoded = %d" % len(covered))
P("   indirect CALL/JMP      = %d" % len(insA))
P("## PASS-B: gap scan of 0xFF bytes not covered by PASS-A")
P("   extra indirect CALL/JMP = %d" % len(insB))
P("## UNION = %d sites" % len(union))
report.update(dict(passA_insns=len(covered), passA_indirect=len(insA),
                   passB_indirect=len(insB), union=len(union)))
P("")

# classify forms
def form(o):
    if o.startswith("dword ptr [0x") or o.startswith("ptr [0x"):
        return "ABS_IAT  " + o
    if "*" in o:
        return "JUMPTABLE " + o
    if "ptr [" in o:
        return "STRUCT_IND " + o
    return "REG_IND " + o

fc = collections.Counter(form(h["ops"]) for h in union.values())
P("## form histogram (top 40)")
for k, n in fc.most_common(40):
    P("   %-60s x%d" % (k, n))
report["forms"] = dict(fc)
P("")

# dedicated jump-table (indexed) forms
jt = [h for h in union.values() if "*" in h["ops"]]
P("## indexed jump-table forms (jmp/call [reg*scale + disp])  -> %d sites" % len(jt))
for h in sorted(jt, key=lambda x: x["rva"]):
    P("   %08x  %s %s   bytes=%s  [%s]" % (h["rva"], h["mn"], h["ops"], h["bytes"], h["source"]))
report["jump_table_sites"] = [dict(rva=h["rva"], ops=h["ops"], source=h["source"]) for h in jt]
P("")

# ---------- PART: address-of-function immediates inside text ----------
P("## PART 4 - immediate constants that are addresses inside text")
addr_lo, addr_hi = IB + TEXT_LO, IB + TEXT_HI
ao = []
i = PLO
while i < PHI - 5:
    b0 = IMG[i]
    v = None; n = 0
    if b0 == 0x68:
        v = struct.unpack("<I", IMG[i+1:i+5])[0]; n = 5
    elif 0xB8 <= b0 <= 0xBF:
        v = struct.unpack("<I", IMG[i+1:i+5])[0]; n = 5
    if v is not None and addr_lo <= v < addr_hi and cov_bool[i - PLO]:
        ao.append((i, v))
        i += n
    else:
        i += 1
P("   hits = %d ; distinct targets = %d" % (len(ao), len(set(v for _, v in ao))))
report["addr_of_immediates"] = len(ao)
P("")

# ---------- PART 5 - function pointer tables ----------
P("## PART 5 - 4-byte values in present bytes that point into text")
addr_lo, addr_hi = IB + TEXT_LO, IB + TEXT_HI
cand = collections.Counter(); locs = collections.defaultdict(list)
for (s, a, b) in SPANS:
    for off in range(a, b - 3):
        v = struct.unpack("<I", IMG[off:off+4])[0]
        if addr_lo <= v < addr_hi:
            cand[v] += 1
            if len(locs[v]) < 12:
                locs[v].append(off)
P("   distinct text targets = %d ; total dword hits = %d" % (len(cand), sum(cand.values())))
strong = [(v, cand[v]) for v in cand if IMG[v-IB-1] in (0xCC, 0xC3) and v-IB-1 >= 0]
P("   targets preceded by CC/C3 (function-start evidence) = %d" % len(strong))
report["dword_text_targets"] = len(cand)
report["dword_text_targets_strong"] = len(strong)
P("")
P("## contiguous pointer-table runs (>=8 consecutive in-text dwords, step 4)")
runs = []
for (s, a, b) in SPANS:
    run = []
    off = a
    while off + 4 <= b:
        v = struct.unpack("<I", IMG[off:off+4])[0]
        if addr_lo <= v < addr_hi:
            run.append((off, v))
        else:
            if len(run) >= 8:
                runs.append(run)
            run = []
        off += 4
    if len(run) >= 8:
        runs.append(run)
P("   runs found = %d" % len(runs))
report["contiguous_runs"] = []
for r in runs[:80]:
    a0 = r[0][0]; n = len(r)
    tgt = [v for (_, v) in r]
    P("   off=%08x n=%3d span=%08x..%08x  first3=%s" % (a0, n, min(tgt), max(tgt), ["%x" % t for t in tgt[:3]]))
    report["contiguous_runs"].append(dict(off="%08x" % a0, n=n, min="%08x" % min(tgt), max="%08x" % max(tgt)))
if len(runs) > 80:
    P("   ... (%d more)" % (len(runs) - 80))
P("")

# ---------- PART 6 - absolute references to audited entries ----------
P("## PART 6 - absolute (dword) references to audited function entries, ALL present bytes")
FOCUS = [(0x87C110, "decoder#1"), (0x87D5A0, "decoder#2"), (0x87BE00, "read-primitive"),
         (0x87BA50, "read-thunk"), (0x87A890, "len-writer"), (0x85E6F0, "TQOS-dispatcher"),
         (0x87ED70, "helperA"), (0x87EDB0, "helperB"), (0x87BFD0, "helper"), (0x87C0E0, "helper")]
fh = {}
for rva, name in FOCUS:
    va = IB + rva
    hits = []
    pat = struct.pack("<I", va)
    for (s, a, b) in SPANS:
        j = IMG.find(pat, a, b)
        while j >= 0:
            hits.append(j); j = IMG.find(pat, j + 1, b)
    fh[name] = ["%x" % x for x in hits]
    P("   %-16s VA=%08x  dword-hits=%d %s" % (name, va, len(hits), ["%x" % x for x in hits[:12]]))
report["focus_dword_hits"] = fh
P("")

# ---------- PART 7 - call targets that reach the audited entries via patterns ----------
P("## PART 7 - indirect-call operands whose base register was loaded with a text address (module-offset style)")
P("   (scan for 'mov reg, imm32-in-text' immediately feeding a nearby indirect call/jmp)")
immmov = {}
i = PLO
while i < PHI - 5:
    b0 = IMG[i]
    if 0xB8 <= b0 <= 0xBF:
        reg = b0 - 0xB8
        v = struct.unpack("<I", IMG[i+1:i+5])[0]
        if addr_lo <= v < addr_hi:
            immmov[i] = ("%s" % c.md.reg_name([c.capstone.x86.X86_REG_EAX, c.capstone.x86.X86_REG_ECX,
                                    c.capstone.x86.X86_REG_EDX, c.capstone.x86.X86_REG_EBX,
                                    c.capstone.x86.X86_REG_ESP, c.capstone.x86.X86_REG_EBP,
                                    c.capstone.x86.X86_REG_ESI, c.capstone.x86.X86_REG_EDI][reg]), v)
    i += 1
P("   'mov reg, <text addr>' sites = %d" % len(immmov))
report["movreg_textaddr"] = len(immmov)
P("")

c.w(os.path.join(c.EV, "c01_indirect_scan.txt"), "\n".join(out))
rows = ["site_rva\tsite_va\tmnemonic\toperand\tform\tbytes\tsource"]
for h in sorted(union.values(), key=lambda x: x["rva"]):
    rows.append("%08x\t%08x\t%s\t%s\t%s\t%s\t%s" % (h["rva"], h["va"], h["mn"], h["ops"],
                form(h["ops"]), h["bytes"], h["source"]))
c.w(os.path.join(c.EV, "c01_indirect_union.tsv"), "\n".join(rows))
c.w(os.path.join(c.EV, "c01_indirect_scan.json"), json.dumps(report, indent=1))
print("\n".join(out))
#!/usr/bin/env python3
"""Section-bounded, read-only data-flow closure for five CA8xxx slots.

The .tvm0 payload is never read.  PE headers are read separately, then each
non-.tvm0 section is seek()/read() independently.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

EXE = Path("codoMP_client_shipRetail.exe")
OUT = Path("scripts/_out")
TMP = Path("scripts/_tmp")
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
IB = 0x00400000
SLOTS = [0x00CA8114, 0x00CA8194, 0x00CA812C, 0x00CA819C, 0x00CA8164]
SLOT_VALUES = {0x00CA8114: 0x00A13726, 0x00CA8194: 0x00A1397A,
               0x00CA812C: 0x00A1378C, 0x00CA819C: 0x00A139A0,
               0x00CA8164: 0x00A1389E}

# Allowed static call pairs in CA8114 -> CA8194 order.
PAIRS = [(0x000269AE, 0x000269C6), (0x0003667A, 0x00036691),
         (0x000AA17B, 0x000AA192), (0x000B2D95, 0x000B2DAC),
         (0x0021DA25, 0x0021DA3C)]

# Header-only read.
with EXE.open("rb") as f:
    dos = f.read(0x40)
    if dos[:2] != b"MZ":
        raise ValueError("not MZ")
    pe_off = struct.unpack_from("<I", dos, 0x3c)[0]
    f.seek(pe_off)
    pe = f.read(24)
    if pe[:4] != b"PE\0\0":
        raise ValueError("not PE")
    nsec = struct.unpack_from("<H", pe, 6)[0]
    opt_size = struct.unpack_from("<H", pe, 20)[0]
    f.seek(pe_off + 24)
    opt = f.read(opt_size)
    if struct.unpack_from("<H", opt, 0)[0] != 0x10b:
        raise ValueError("not PE32")
    image_base = struct.unpack_from("<I", opt, 28)[0]
    entry = struct.unpack_from("<I", opt, 16)[0]
    size_image = struct.unpack_from("<I", opt, 56)[0]
    if image_base != IB:
        raise ValueError("unexpected image base")
    f.seek(pe_off + 24 + opt_size)
    sh = f.read(40 * nsec)

sections = []
for i in range(nsec):
    h = sh[40 * i:40 * (i + 1)]
    name = h[:8].split(b"\0", 1)[0].decode("latin1")
    vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", h, 8)
    chars = struct.unpack_from("<I", h, 36)[0]
    sections.append(dict(i=i, name=name, va=va, vsize=vsize, rawptr=rawptr,
                         rawsize=rawsize, chars=chars, data=None))

# Read permitted section payloads one at a time.  Explicitly never read .tvm0.
with EXE.open("rb") as f:
    for s in sections:
        if s["name"].lower() == ".tvm0":
            continue
        if s["rawsize"]:
            f.seek(s["rawptr"])
            b = f.read(s["rawsize"])
            if len(b) != s["rawsize"]:
                raise IOError("short section read")
            s["data"] = b


def sec_at(rva, raw=False):
    for s in sections:
        span = max(s["vsize"], s["rawsize"])
        if s["va"] <= rva < s["va"] + span:
            if raw and (s["data"] is None or rva - s["va"] >= s["rawsize"]):
                return None
            return s
    return None


def rva_to_off(rva):
    s = sec_at(rva, raw=True)
    return None if s is None else s["rawptr"] + (rva - s["va"])


def read_rva(rva, size):
    s = sec_at(rva, raw=True)
    if s is None:
        return None
    q = rva - s["va"]
    if q < 0 or q + size > s["rawsize"]:
        return None
    return s["data"][q:q + size]


def u32(rva):
    b = read_rva(rva, 4)
    return None if b is None else struct.unpack("<I", b)[0]


def section_name(rva):
    s = sec_at(rva, raw=False)
    return "OUTSIDE" if s is None else "#%d %s" % (s["i"], s["name"])


def is_exec(rva):
    s = sec_at(rva, raw=True)
    return bool(s and (s["chars"] & 0x20000000) and s["name"].lower() != ".tvm0")


md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def decode(rva, max_bytes=256, count=0):
    s = sec_at(rva, raw=True)
    if s is None or not (s["chars"] & 0x20000000):
        return []
    q = rva - s["va"]
    lim = min(max_bytes, s["rawsize"] - q)
    if lim <= 0:
        return []
    return list(md.disasm(s["data"][q:q + lim], IB + rva, count=count))


def text(ins):
    return "%s %s" % (ins.mnemonic, ins.op_str) if ins.op_str else ins.mnemonic


def instr_obj(ins):
    return dict(rva=ins.address - IB, size=ins.size, bytes=ins.bytes.hex(), text=text(ins))


# Export table, restricted to permitted file-backed executable addresses.
def cstr(rva, maxlen=512):
    b = read_rva(rva, maxlen)
    if b is None:
        return ""
    return b.split(b"\0", 1)[0].decode("latin1", "replace")


def parse_exports():
    er, es = struct.unpack_from("<II", opt, 96)
    if not er or read_rva(er, 40) is None:
        return []
    n_fun = u32(er + 24)
    addr_fun = u32(er + 28)
    n_name = u32(er + 32)
    addr_name = u32(er + 36)
    out = []
    if n_fun is None or addr_fun is None:
        return out
    for i in range(min(n_fun, 0x10000)):
        rva = u32(addr_fun + 4 * i)
        name = ""
        if i < (n_name or 0) and addr_name is not None:
            nr = u32(addr_name + 4 * i)
            if nr is not None:
                name = cstr(nr)
        if rva is not None and is_exec(rva):
            out.append(dict(rva=rva, name=name))
    return out


exports = parse_exports()
roots = [(entry, entry, "PE_ENTRY")]
for e in exports:
    roots.append((e["rva"], e["rva"], "EXPORT:%s" % e["name"]))

# Conservative clean CFG: fallthrough, direct Jcc/JMP, and direct CALL targets.
cfg_ins = {}
cfg_owners = collections.defaultdict(set)
cfg_funcs = collections.defaultdict(set)
cfg_edges = []
seen = set()
q = collections.deque(roots)
while q:
    root, func, provenance = q.popleft()
    key = (func, root)
    if key in seen or not is_exec(root):
        continue
    seen.add(key)
    cur = root
    while is_exec(cur):
        ins = next(iter(decode(cur, 15, 1)), None)
        if ins is None:
            break
        a = ins.address - IB
        if a != cur:
            break
        existing = cfg_ins.get(a)
        if existing is not None:
            cfg_owners[a].add(root)
            cfg_funcs[a].add(func)
            break
        cfg_ins[a] = ins
        cfg_owners[a].add(root)
        cfg_funcs[a].add(func)
        m, ops = ins.mnemonic, ins.operands
        if m in ("ret", "retn", "iret", "iretd", "ud2", "int3"):
            break
        if m == "call":
            if ops and ops[0].type == X86_OP_IMM:
                t = int(ops[0].imm) - IB
                cfg_edges.append((a, t, "CALL"))
                if is_exec(t):
                    q.append((t, t, "CALL_TARGET"))
            cur += ins.size
            continue
        if m.startswith("j"):
            if ops and ops[0].type == X86_OP_IMM:
                t = int(ops[0].imm) - IB
                cfg_edges.append((a, t, "JCC" if m != "jmp" else "JMP"))
                if is_exec(t):
                    q.append((root, func, "BRANCH"))
            if m == "jmp":
                break
            cur += ins.size
            continue
        cur += ins.size

# Exact raw FF15/FF25 references to each target slot; scan only permitted sections.
raw_refs = []
for s in sections:
    if s["data"] is None:
        continue
    b = s["data"]
    for j in range(max(0, len(b) - 5)):
        if b[j] == 0xFF and b[j + 1] in (0x15, 0x25):
            slot = struct.unpack_from("<I", b, j + 2)[0]
            if slot not in SLOTS:
                continue
            rva = s["va"] + j
            ins = next(iter(decode(rva, 15, 1)), None)
            self_ok = False
            self_text = "FAIL"
            if ins is not None and ins.address - IB == rva:
                self_text = text(ins)
                self_ok = (ins.size == 6 and ins.bytes[:2] == bytes((0xFF, b[j + 1])) and
                           ((ins.mnemonic == "call" and b[j + 1] == 0x15) or
                            (ins.mnemonic == "jmp" and b[j + 1] == 0x25)))
            raw_refs.append(dict(rva=rva, slot=slot, opcode="FF%02X" % b[j + 1],
                                 section="#%d %s" % (s["i"], s["name"]),
                                 is_exec=bool(s["chars"] & 0x20000000),
                                 self_ok=self_ok, self_text=self_text,
                                 raw=b[j:j + 6].hex()))
raw_refs.sort(key=lambda x: (x["slot"], x["rva"]))


def reg_num(op):
    return int(op.reg) if op.type == X86_OP_REG else None


def reads_eax(ins):
    for op in ins.operands:
        if op.type == X86_OP_REG and int(op.reg) == 0:
            return True
        if op.type == X86_OP_MEM and (int(op.mem.base) == 0 or int(op.mem.index) == 0):
            return True
    return False


def writes_eax(ins):
    if not ins.operands:
        return False
    op = ins.operands[0]
    if op.type == X86_OP_REG and int(op.reg) == 0:
        if ins.mnemonic in ("cmp", "test", "push", "call", "jmp"):
            return False
        return True
    return False


def post_steps(ref, limit=16):
    steps = []
    cur = ref["rva"] + 6
    for z in decode(cur, 160, limit):
        rva = z.address - IB
        if rva < cur:
            continue
        steps.append(dict(rva=rva, size=z.size, bytes=z.bytes.hex(), text=text(z),
                          reads_eax=reads_eax(z), writes_eax=writes_eax(z)))
        if z.mnemonic in ("ret", "retn", "iret", "iretd", "ud2", "int3", "jmp"):
            break
    return steps


def classify_post(steps):
    if not steps:
        return dict(kind="UNKNOWN", first=None, overwrites_ret=False)
    first = steps[0]
    kind = "OTHER"
    if first["reads_eax"]:
        kind = "READ_EAX_FIRST"
    elif first["writes_eax"]:
        kind = "OVERWRITE_EAX_FIRST"
    elif first["text"].startswith("push"):
        kind = "PUSH_FIRST"
    elif first["text"].startswith("call"):
        kind = "CALL_FIRST"
    return dict(kind=kind, first=first, overwrites_ret=first["writes_eax"])


for r in raw_refs:
    r["ins"] = cfg_ins.get(r["rva"])
    r["clean_cfg"] = r["ins"] is not None
    r["cfg_roots"] = sorted(cfg_owners.get(r["rva"], set()))
    r["cfg_funcs"] = sorted(cfg_funcs.get(r["rva"], set()))
    r["post"] = post_steps(r)
    r["post_class"] = classify_post(r["post"])

# Exact local predecessor decode: build a table of instructions ending at rva.
def predecessor_nodes(target, max_back=32):
    out = []
    for k in range(1, max_back + 1):
        st = target - k
        z = decode(st, k + 16, 1)
        if z and z[0].address - IB == st and st + z[0].size == target:
            out.append(instr_obj(z[0]))
    return out


for r in raw_refs:
    r["pred"] = predecessor_nodes(r["rva"])

# Selected exact mov reg,[slot]; call reg patterns.  These are byte-hit
# candidates, explicitly not function-boundary claims.
movcall = []
for s in sections:
    if s["data"] is None:
        continue
    b = s["data"]
    for slot in SLOTS:
        for modrm in range(5, 64, 8):  # 8B /0 with mod=00, rm=disp32
            pat = b"\x8b" + bytes((modrm,)) + struct.pack("<I", slot)
            pos = 0
            while True:
                pos = b.find(pat, pos)
                if pos < 0:
                    break
                rva = s["va"] + pos
                ins = next(iter(decode(rva, 15, 1)), None)
                if ins and ins.address - IB == rva and ins.mnemonic == "mov":
                    # Find first exact call reg after the load, allowing a small
                    # straight-line glue window and stopping on control transfer.
                    found = None
                    cur = rva + ins.size
                    for z in decode(cur, 48, 10):
                        if z.mnemonic == "call" and z.operands and z.operands[0].type == X86_OP_REG:
                            found = instr_obj(z)
                            break
                        if z.mnemonic in ("ret", "retn", "jmp", "call"):
                            break
                        cur += z.size
                    if found:
                        movcall.append(dict(load=instr_obj(ins), call=found,
                                            section="#%d %s" % (s["i"], s["name"]),
                                            slot=slot))
                pos += 1
movcall.sort(key=lambda x: x["load"]["rva"])
movcall = list({(x["load"]["rva"], x["call"]["rva"]): x for x in movcall}.values())

# CA819C contiguous push imm32 predecessors.  Only exact adjacent decode is counted.
imm_rows = []
for r in [x for x in raw_refs if x["slot"] == 0x00CA819C]:
    for p in r["pred"]:
        if p["text"].startswith("push 0x"):
            try:
                v = int(p["text"].split("0x", 1)[1], 16)
            except ValueError:
                continue
            if 0x081A5200 <= v <= 0x081A5700:
                imm_rows.append(dict(ref=r["rva"], push=p["rva"], value=v,
                                     text=p["text"], cfg=r["clean_cfg"]))
                break
imm_rows.sort(key=lambda x: x["ref"])

# Pair-level exact local matrix.
pair_rows = []
for a, b in PAIRS:
    ra = next((r for r in raw_refs if r["rva"] == a and r["slot"] == 0x00CA8114), None)
    rb = next((r for r in raw_refs if r["rva"] == b and r["slot"] == 0x00CA8194), None)
    if ra is None or rb is None:
        continue
    pair_rows.append(dict(a=a, b=b, delta=b - a,
                          cfg_a=ra["clean_cfg"], cfg_b=rb["clean_cfg"],
                          funcs_a=ra["cfg_funcs"], funcs_b=rb["cfg_funcs"],
                          a_post=[x["text"] for x in ra["post"][:8]],
                          b_post=[x["text"] for x in rb["post"][:6]],
                          bytes32=read_rva(a, 32).hex() if read_rva(a, 32) else None,
                          same32=bool(read_rva(a, 32) == read_rva(b, 32)),
                          same64=bool(read_rva(a, 64) == read_rva(b, 64))))

# Entry sentinel-local table scan: CA8000..CA8800 and exact entry neighborhood.
entry_rva = 0x0E5DC690
entry_slot_rva = 0x0E9DC665 - IB
entry_value = u32(entry_slot_rva)
entry_neighbors = []
for idx in range(-4, 5):
    rva = entry_slot_rva + 4 * idx
    entry_neighbors.append(dict(offset=4 * idx, rva=rva, value=u32(rva)))
sent_rows = []
for idx in range(512):
    rva = 0x00CA8000 - IB + 4 * idx
    v = u32(rva)
    if v is not None and 0x80000000 <= v <= 0x8FFFFFFF:
        sent_rows.append(dict(index=idx, va=0x00CA8000 + 4 * idx, value=v))
same_80000001 = [x for x in sent_rows if x["value"] == 0x80000001]
entry_post = [instr_obj(z) for z in decode(entry_rva, 128)][:16]

# Runtime data global values directly named by the pair sequences.
pair_global_windows = {}
for a, b in PAIRS:
    ctx = [x for x in decode(a - 16, 96) if x.address - IB >= a - 16]
    vals = []
    for z in ctx:
        for op in z.operands:
            if op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                d = int(op.mem.disp) & 0xffffffff
                if d > 0x00400000:
                    vals.append((z.address - IB, text(z), d, u32(d - IB)))
    pair_global_windows["%08X:%08X" % (a, b)] = vals

result = dict(
    sha256=hashlib.sha256(b"".join(s["data"] for s in sections if s["data"] is not None)).hexdigest(),
    sections=[{k: v for k, v in s.items() if k != "data"} for s in sections],
    image_base=image_base, entry_rva=entry, size_image=size_image,
    exports=exports, cfg_instruction_count=len(cfg_ins), cfg_edges=len(cfg_edges),
    refs=raw_refs, movcall=movcall, imm_rows=imm_rows, pairs=pair_rows,
    entry=dict(rva=entry_rva, slot_rva=entry_slot_rva, slot_value=entry_value,
               neighbors=entry_neighbors, post=entry_post,
               sentinel_count=len(sent_rows), sentinel_rows=sent_rows,
               same_80000001=same_80000001),
    pair_global_windows=pair_global_windows,
)
(TMP / "ca8xxx_dataflow_closure.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

print("sections")
for s in sections:
    print(" %d %-6s va=%08X vsize=%X raw=%X ptr=%X data=%s" % (
        s["i"], s["name"], s["va"], s["vsize"], s["rawsize"], s["rawptr"],
        "EXCLUDED" if s["data"] is None else "READ"))
print("entry=%08X exports=%d cfg_ins=%d cfg_edges=%d refs=%d" % (
    entry, len(exports), len(cfg_ins), len(cfg_edges), len(raw_refs)))
for slot in SLOTS:
    rs = [r for r in raw_refs if r["slot"] == slot]
    print("SLOT %08X value=%08X refs=%d ff15=%d ff25=%d clean=%d overwrite_ret=%d" % (
        slot, SLOT_VALUES[slot], len(rs), sum(r["opcode"] == "FF15" for r in rs),
        sum(r["opcode"] == "FF25" for r in rs), sum(r["clean_cfg"] for r in rs),
        sum(r["post_class"]["overwrites_ret"] for r in rs)))
print("movcall", [(hex(x["slot"]), hex(x["load"]["rva"]), x["load"]["text"], hex(x["call"]["rva"]), x["call"]["text"]) for x in movcall])
print("imm_rows", len(imm_rows), [(hex(x["ref"]), hex(x["value"])) for x in imm_rows])
print("entry local", hex(entry_value), [(x["offset"], None if x["value"] is None else hex(x["value"])) for x in entry_neighbors])
print("sentinel", len(sent_rows), "same80000001", same_80000001)
print("pairs")
for p in pair_rows:
    print(hex(p["a"]), hex(p["b"]), "delta", p["delta"], "cfg", p["cfg_a"], p["cfg_b"], "same32", p["same32"], "same64", p["same64"])
print("wrote", TMP / "ca8xxx_dataflow_closure.json")

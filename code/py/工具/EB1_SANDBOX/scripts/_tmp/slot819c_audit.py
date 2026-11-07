# -*- coding: utf-8 -*-
# Read-only audit helper. Never opens, scans, disassembles, or hashes .tvm0 bytes.
import csv, json, struct
from collections import defaultdict, deque, Counter
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

EXE = Path('codoMP_client_shipRetail.exe')
CSV = Path('scripts/_out/high_reuse_slot_detail.csv')
IB = 0x400000
SLOT = 0x00CA819C
D = EXE.read_bytes()

# PE section table supplied from the independently parsed PE header. .tvm0 is
# retained only as metadata so every scanner can explicitly exclude section [#5].
SECS = [
    dict(i=0, name='.tp3', va=0x00001000, vs=0x08A689A, rs=0x593000, pr=0x001000, ch=0x60000020),
    dict(i=1, name='.tp3', va=0x008A8000, vs=0x016DA70, rs=0x16E000, pr=0x594000, ch=0x40000040),
    dict(i=2, name='.tp3', va=0x00A16000, vs=0xDBB1CC0, rs=0x062000, pr=0x702000, ch=0xC0000040),
    dict(i=3, name='.tp3', va=0x0E5C8000, vs=0x0000031, rs=0x001000, pr=0x764000, ch=0xC0000040),
    dict(i=4, name='.tp3', va=0x0E5C9000, vs=0x0009228, rs=0x00A000, pr=0x765000, ch=0x40000040),
    dict(i=5, name='.tvm0', va=0x0E5D3000, vs=0x0004000, rs=0x002000, pr=0x76F000, ch=0x60000020),
    dict(i=6, name='.tp3', va=0x0E5D7000, vs=0x0082000, rs=0x006000, pr=0x771000, ch=0xE0000020),
]

def sec(rva):
    for s in SECS:
        if s['va'] <= rva < s['va'] + max(s['vs'], s['rs']):
            return s
    return None

def off(rva):
    s = sec(rva)
    if not s: return None
    d = rva - s['va']
    return s['pr'] + d if 0 <= d < s['rs'] else None

def u32(rva):
    o = off(rva)
    return struct.unpack_from('<I', D, o)[0] if o is not None and o + 4 <= len(D) else None

def section_name(rva):
    s = sec(rva)
    return '%s#%d' % (s['name'], s['i']) if s else 'OUT'

def is_code(rva):
    s = sec(rva)
    return bool(s and s['name'] != '.tvm0' and (s['ch'] & 0x20000000))

def exe_bytes(rva, n):
    o = off(rva)
    return D[o:o+n] if o is not None else b''

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def one(rva):
    o = off(rva)
    if o is None: return None
    return next(md.disasm(D[o:o+15], IB + rva, count=1), None)

def ins_text(ins):
    return '%s %s' % (ins.mnemonic, ins.op_str) if ins else ''

def read_csv_rows():
    with CSV.open(newline='', encoding='utf-8') as f:
        return [r for r in csv.DictReader(f) if int(r['slot'],16) == SLOT]

rows = read_csv_rows()
assert len(rows) == 36, len(rows)
refs = sorted(int(r['ref_rva'], 16) for r in rows)

# Minimal map of instruction starts, seeded from the CSV reference locations and
# their claimed candidates. This is deliberately labeled CANDIDATE_MAP, not CFG.
candidate_starts = [int(r['candidate_func'], 16) for r in rows if r.get('candidate_func')]
starts = set(refs) | set(candidate_starts)
for s in candidate_starts:
    x = one(s)
    if x:
        starts.add(s)

# Check each candidate address against a standard prologue and local byte pattern.
prologue_hits = {}
for r in rows:
    cf = r.get('candidate_func', '')
    if not cf:
        prologue_hits[int(r['ref_rva'], 16)] = False
        continue
    c = int(cf, 16)
    b = exe_bytes(c, 8)
    prologue_hits[int(r['ref_rva'], 16)] = {
        'candidate': c,
        'bytes': b.hex(),
        'push_ebp_mov_ebp': b.startswith(b'\x55\x8b\xec'),
        'push_imm_then_mov_ebp': b[:2] == b'\x6a\xff' or b[:2] == b'\x68',
    }

# Context rows, decoded from a conservative boundary: own instruction plus up
# to 64 bytes before and 64 bytes after at the exact instruction starts only.
ctx = []
for r in rows:
    rv = int(r['ref_rva'], 16)
    ins = one(rv)
    before = []
    x = rv
    # Walk backward only across a span that itself has a self-consistent decode
    # ending exactly at rv. If no such span exists, report UNKNOWN instead of
    # pretending the bytes are instructions.
    back_ok = None
    back_start = None
    for delta in range(1, 65):
        s = rv - delta
        if not is_code(s) or off(s) is None: continue
        seq = list(md.disasm(D[off(s):off(rv) + ins.size if ins else off(rv)+6], IB + s))
        if seq and seq[-1].address == IB + rv and sum(z.size for z in seq) == delta:
            back_ok = True; back_start = s
        # Continue to find the largest exact ending span, but retain last success.
    if back_start is not None:
        seq = list(md.disasm(D[off(back_start):off(rv)+64], IB + back_start))
        for z in seq:
            if z.address < IB + rv:
                before.append((z.address-IB, z.bytes.hex(), ins_text(z)))
            elif z.address == IB + rv:
                break
    post = []
    if ins:
        cur = rv + ins.size
        seq = list(md.disasm(D[off(cur):off(cur)+64], IB + cur))
        for z in seq:
            if z.address - IB >= rv + ins.size + 64: break
            post.append((z.address-IB, z.bytes.hex(), ins_text(z)))
    # Template signals within the local region.
    pre_bytes = exe_bytes(rv-64, 64)
    post_bytes = exe_bytes(rv+6, 64)
    pre_ins = []
    for delta in range(64):
        s = rv - 64 + delta
        z = one(s)
        if z and z.address == IB + s:
            pre_ins.append((s, z.bytes.hex(), ins_text(z)))
    # choose the longest exact backward decode if available; else expose all
    # candidate starts that decode to rv, but never assert them as instructions.
    exact_back = []
    for delta in range(1, 65):
        s = rv - delta
        if not is_code(s) or off(rv) is None: continue
        seq = list(md.disasm(D[off(s):off(rv)+6], IB+s))
        if seq and seq[-1].address == IB+rv and sum(z.size for z in seq) == delta:
            exact_back.append(s)
    ctx.append(dict(
        ref_rva='0x%08X' % rv, ref_va='0x%08X' % (IB+rv),
        raw=exe_bytes(rv, 6).hex(), self=ins_text(ins),
        slot='0x%08X' % SLOT, slot_value='0x%08X' % u32(SLOT-IB),
        boundary='CFG_UNKNOWN' if not exact_back else 'LOCAL_EXACT_BACKWARD',
        back_start=('0x%08X' % max(exact_back)) if exact_back else '',
        exact_back_starts=' '.join('0x%08X' % x for x in exact_back),
        pre64=pre_bytes.hex(), post64=post_bytes.hex(),
        before=before, post=post,
        candidate=('0x%08X' % int(r['candidate_func'],16)) if r.get('candidate_func') else '',
        candidate_kind=r.get('candidate_kind',''),
        candidate_bytes=json.dumps(prologue_hits.get(rv), sort_keys=True),
        old_cfg_reachable=r.get('cfg_reachable',''),
        old_cfg_roots=r.get('cfg_roots',''),
        old_boundary_conf=r.get('boundary_confidence',''),
    ))

# Raw reference census for this slot, excluding .tvm0 explicitly.
all_raw = []
for s in SECS:
    if s['name'] == '.tvm0': continue
    b = D[s['pr']:s['pr']+s['rs']]
    for j in range(len(b)-6):
        if b[j]==0xff and b[j+1] in (0x15,0x25):
            v=struct.unpack_from('<I', b, j+2)[0]
            if v == SLOT:
                all_raw.append((s['va']+j, b[j+1], b[j:j+6].hex()))
all_raw.sort()
raw_rvas = [x[0] for x in all_raw]
# The authoritative 36-row list comes from the supplied CSV; raw_census is a diagnostic.

# Look for identical slot operands and references in local windows, excluding .tvm0.
slot_family = []
for rv in refs:
    near=[]
    for x in all_raw:
        d=x[0]-rv
        if d != 0 and -64 <= d <= 64:
            near.append(('0x%08X' % x[0], d, x[2]))
    slot_family.append(dict(ref_rva='0x%08X' % rv, same_slot_within_64=near))

# Direct-call candidate edges, using only bytes in executable non-.tvm0 sections,
# and labeling as raw E8 candidates unless the call start is already in our map.
direct=[]
for s in SECS:
    if s['name']=='.tvm0' or not (s['ch'] & 0x20000000): continue
    b=D[s['pr']:s['pr']+s['rs']]
    for j in range(len(b)-5):
        if b[j]==0xe8:
            t=s['va']+j+5+struct.unpack_from('<i',b,j+1)[0]
            if t in refs:
                direct.append((s['va']+j,t))
print(json.dumps({
  'rows':len(rows),'refs':['0x%08X'%x for x in refs],
  'slot_value':'0x%08X'%u32(SLOT-IB),
  'slot_section':section_name(SLOT-IB),
  'slot_file_backed':off(SLOT-IB) is not None,
  'target_rva':'0x%08X'%(u32(SLOT-IB)-IB),
  'target_section':section_name(u32(SLOT-IB)-IB),
  'target_file_backed':off(u32(SLOT-IB)-IB) is not None,
  'csv_refs':len(refs), 'raw_census_diagnostic':len(all_raw),
}, indent=2))
Path('scripts/_tmp/slot819c_audit.json').write_text(json.dumps(ctx,indent=2),encoding='utf-8')
print('wrote scripts/_tmp/slot819c_audit.json')

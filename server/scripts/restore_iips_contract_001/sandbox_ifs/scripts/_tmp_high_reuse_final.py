from pathlib import Path
import csv, struct, collections, hashlib
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

EXE = Path('codoMP_client_shipRetail.exe')
OUT = Path('scripts/_out')
IB = 0x400000
SLOTS = [0x00CA8114, 0x00CA8194, 0x00CA812C, 0x00CA819C, 0x00CA8164]
ENTRY = 0x0E5DC690
ENTRY_SLOT = 0x0E9DC665

D = EXE.read_bytes()
pe = struct.unpack_from('<I', D, 0x3c)[0]
nsec = struct.unpack_from('<H', D, pe + 6)[0]
opt = pe + 24
optsz = struct.unpack_from('<H', D, pe + 20)[0]
secoff = opt + optsz
SECS = []
for i in range(nsec):
    h = secoff + 40 * i
    name = D[h:h+8].split(b'\0')[0].decode('latin1')
    vs, va, rs, pr = struct.unpack_from('<IIII', D, h + 8)
    ch = struct.unpack_from('<I', D, h + 36)[0]
    SECS.append(dict(i=i, name=name, va=va, vs=vs, rs=rs, pr=pr, ch=ch))

def sec_at(rva):
    for s in SECS:
        if s['va'] <= rva < s['va'] + max(s['vs'], s['rs']):
            return s
    return None

def off(rva):
    s = sec_at(rva)
    if not s:
        return None
    q = rva - s['va']
    return s['pr'] + q if 0 <= q < s['rs'] else None

def u32(rva):
    o = off(rva)
    return struct.unpack_from('<I', D, o)[0] if o is not None and o + 4 <= len(D) else None

def is_exec(rva):
    s = sec_at(rva)
    return bool(s and s['name'] != '.tvm0' and (s['ch'] & 0x20000000) and off(rva) is not None)

def cstr(rva):
    o = off(rva)
    if o is None:
        return ''
    return D[o:o+512].split(b'\0', 1)[0].decode('latin1', 'replace')

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm(start, maxlen=0x10000):
    o = off(start)
    s = sec_at(start)
    if o is None or not is_exec(start):
        return []
    lim = min(maxlen, len(D) - o, s['vs'] - (start - s['va']))
    return list(md.disasm(D[o:o+lim], IB + start))

def exports():
    er, es = struct.unpack_from('<II', D, opt + 96)
    if not er or off(er) is None:
        return []
    nf = u32(er + 24); af = u32(er + 28); nn = u32(er + 32); an = u32(er + 36)
    out = []
    for i in range(nf):
        rva = u32(af + 4 * i)
        name = ''
        if i < nn:
            ao = off(an + 4 * i)
            if ao is not None:
                nr = u32(an + 4 * i)
                if nr is not None:
                    name = cstr(nr)
        if rva is not None and is_exec(rva):
            out.append((rva, name))
    return out

EXPORTS = exports()
EXPORT_MAP = dict(EXPORTS)

# Conservative direct/fallthrough graph rooted only at real PE exports and the PE entry.
cfg_ins = {}
cfg_owner = collections.defaultdict(set)
queue = collections.deque((r, r) for r, _ in EXPORTS)
queue.append((ENTRY, ENTRY))
processed = set()
while queue:
    root, start = queue.popleft()
    key = (root, start)
    if key in processed or not is_exec(start):
        continue
    processed.add(key)
    for x in disasm(start, maxlen=0x20000):
        a = x.address - IB
        cfg_ins[a] = x
        cfg_owner[a].add(root)
        m = x.mnemonic
        ops = x.operands
        if m in ('ret', 'retn', 'iret', 'iretd', 'ud2', 'int3'):
            break
        if m == 'call':
            if ops and ops[0].type == CS_OP_IMM:
                t = ops[0].imm - IB
                if is_exec(t):
                    queue.append((t, t))
            continue
        if m.startswith('j'):
            if ops and ops[0].type == CS_OP_IMM:
                t = ops[0].imm - IB
                if is_exec(t):
                    queue.append((root, t))
            if m == 'jmp':
                break
            continue
        nxt = a + x.size
        if is_exec(nxt):
            queue.append((root, nxt))

# Raw exact FF15/FF25 references to the five slots, excluding .tvm0.
refs = []
for s in SECS:
    if s['name'] == '.tvm0':
        continue
    b = D[s['pr']:s['pr'] + s['rs']]
    for j in range(len(b) - 6):
        if b[j] == 0xff and b[j+1] in (0x15, 0x25):
            slot = struct.unpack_from('<I', b, j + 2)[0]
            if slot in SLOTS:
                refs.append(dict(rva=s['va'] + j, slot=slot, ophex='FF%02X' % b[j+1], raw=b[j:j+6].hex()))
refs.sort(key=lambda x: (x['slot'], x['rva']))

# Existing candidate search is retained only as a LOW-confidence orientation, never as a boundary proof.
cand = {}
cp = OUT / 'high_reuse_slot_detail.csv'
if cp.exists():
    for r in csv.DictReader(cp.open(encoding='utf-8')):
        cand[int(r['ref_rva'], 16)] = r

slot_info = {}
for slot in SLOTS:
    value = u32(slot - IB)
    target_rva = value - IB
    ts = sec_at(target_rva)
    slot_info[slot] = dict(value=value, target_rva=target_rva, target_section=('#%d %s' % (ts['i'], ts['name'])) if ts else 'OUTSIDE',
                           target_backed=off(target_rva) is not None, table_index=(slot - 0x00CA8000)//4)

# Build rows.
rows = []
for x in refs:
    rva = x['rva']; slot = x['slot']
    z = next(md.disasm(D[off(rva):off(rva)+16], IB + rva, count=1), None)
    self_ok = bool(z and z.size == 6 and z.mnemonic in ('call','jmp') and z.op_str == 'dword ptr [0x%x]' % slot)
    owners = sorted(cfg_owner.get(rva, set()))
    cfg_exact = bool(owners)
    c = cand.get(rva, {})
    if cfg_exact:
        root = owners[0]
        bstat = 'CFG_INSTRUCTION_START'
        bconf = 'HIGH'
        fnroot = '0x%08X' % root
        fnname = EXPORT_MAP.get(root, '')
    elif c.get('candidate_func'):
        bstat = 'LINEAR_CANDIDATE_ONLY'
        bconf = 'LOW'
        fnroot = c.get('candidate_func', '')
        fnname = EXPORT_MAP.get(int(fnroot, 16), '') if fnroot else ''
    else:
        bstat = 'UNRESOLVED'
        bconf = 'UNKNOWN'
        fnroot = ''
        fnname = ''
    preo = max(0, off(rva) - 64)
    posto = min(len(D), off(rva) + 70)
    rows.append(dict(
        slot_va='0x%08X' % slot, slot_table_index=str(slot_info[slot]['table_index']), slot_value='0x%08X' % slot_info[slot]['value'],
        target_va='0x%08X' % slot_info[slot]['value'], target_rva='0x%08X' % slot_info[slot]['target_rva'],
        target_section=slot_info[slot]['target_section'], target_file_backed='YES' if slot_info[slot]['target_backed'] else 'NO',
        ref_rva='0x%08X' % rva, ref_va='0x%08X' % (IB + rva), opcode=x['ophex'], raw_bytes=x['raw'],
        self_decode=(z.mnemonic + ' ' + z.op_str) if z else 'FAIL', self_decode_exact='YES' if self_ok else 'NO',
        cfg_instruction_start='YES' if cfg_exact else 'NO', cfg_roots=' '.join('0x%08X' % q for q in owners),
        boundary_status=bstat, boundary_confidence=bconf, function_root=fnroot, function_name=fnname,
        candidate_kind=c.get('candidate_kind', ''), candidate_linear_extent=((c.get('func_start','') or '-') + '..' + (c.get('func_end_linear','') or '-')),
        pre64=D[preo:off(rva)].hex(), post64=D[off(rva)+6:posto].hex()))

fields = list(rows[0].keys())
with (OUT / 'high_reuse_slot_final_refs.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

# Text report: every row gets raw +/-64 and a self-decoded forward window.
lines = []
lines.append('HIGH-REUSE CA8xxx SLOT CALLER CLUSTER FINAL AUDIT')
lines.append('Input SHA256: %s' % hashlib.sha256(D).hexdigest())
lines.append('Raw refs: %d (FF15=%d FF25=%d)' % (len(rows), sum(r['opcode']=='FF15' for r in rows), sum(r['opcode']=='FF25' for r in rows)))
lines.append('Evidence layers: RAW_PATTERN < SELF_DECODE < CFG_INSTRUCTION_START < FUNCTION_BOUNDARY < RUNTIME_LIVE')
lines.append('CFG roots are PE exports plus the PE entry; indirect targets are not invented.')
lines.append('LINEAR_CANDIDATE_ONLY is deliberately LOW and is not a function-boundary proof.')
lines.append('')
for slot in SLOTS:
    rs = [r for r in rows if r['slot_va'] == '0x%08X' % slot]
    si = slot_info[slot]
    lines.append('=' * 108)
    lines.append('SLOT 0x%08X index=%d value=0x%08X target_rva=0x%08X target=%s raw_backed=%s refs=%d' %
                 (slot, si['table_index'], si['value'], si['target_rva'], si['target_section'], 'YES' if si['target_backed'] else 'NO', len(rs)))
    for r in rs:
        lines.append('-' * 108)
        lines.append('REF %s slot=%s opcode=%s raw=%s self=%s' % (r['ref_rva'], r['slot_va'], r['opcode'], r['raw_bytes'], r['self_decode']))
        lines.append('cfg_exact=%s roots=%s boundary=%s/%s function_root=%s name=%s' % (r['cfg_instruction_start'], r['cfg_roots'] or '-', r['boundary_status'], r['boundary_confidence'], r['function_root'] or '-', r['function_name'] or '-'))
        if r['candidate_kind']:
            lines.append('candidate_linear=%s kind=%s (LOW ONLY)' % (r['candidate_linear_extent'], r['candidate_kind']))
        lines.append('BYTES[-64:%s] %s %s %s' % (r['ref_rva'], r['pre64'], r['raw_bytes'], r['post64']))
        fv = int(r['ref_rva'], 16)
        for q in md.disasm(D[off(fv):off(fv)+64], IB + fv, count=10):
            lines.append('  %08X %-20s %s' % (q.address - IB, q.bytes.hex(), q.mnemonic + ' ' + q.op_str))
    lines.append('')

# Stable local pair relationships.
pair_rows = []
for a in rows:
    if a['slot_va'] != '0x00CA8114':
        continue
    ar = int(a['ref_rva'], 16)
    for b in rows:
        br = int(b['ref_rva'], 16)
        if b['slot_va'] == '0x00CA8194' and ar < br <= ar + 64:
            pair_rows.append((a, b, br - ar))
lines.append('CA8114 -> CA8194 LOCAL PAIRS (<=64 bytes)')
for a, b, dlt in pair_rows:
    lines.append('  %s -> %s delta=+%d  cfg(=%s,%s)  same_static_owner=%s' %
                 (a['ref_rva'], b['ref_rva'], dlt, a['cfg_instruction_start'], b['cfg_instruction_start'],
                  'YES' if a['cfg_roots'] and a['cfg_roots'] == b['cfg_roots'] else 'UNRESOLVED/NO'))
lines.append('')

# Entry sentinel structural comparison.
entry_va = ENTRY_SLOT
entry_rva = entry_va - IB
entry_value = u32(entry_rva)
entry_sec = sec_at(entry_rva)
entry_refs = []
for s in SECS:
    if s['name'] == '.tvm0':
        continue
    b = D[s['pr']:s['pr'] + s['rs']]
    for j in range(len(b) - 6):
        if b[j:j+2] in (b'\xff\x15', b'\xff\x25') and struct.unpack_from('<I', b, j+2)[0] == entry_va:
            entry_refs.append((s['va'] + j, 'FF%02X' % b[j+1], b[j:j+6].hex()))
lines.append('ENTRY SLOT COMPARISON')
lines.append('entry_rva=0x%08X entry_slot=0x%08X slot_value=0x%08X next_dword=0x%08X section=#%d %s slot_file_backed=%s' %
             (ENTRY, entry_va, entry_value, u32(entry_rva + 4), entry_sec['i'], entry_sec['name'], bool(off(entry_rva))))
lines.append('entry exact raw refs=%s' % (' '.join('%08X/%s/%s' % z for z in entry_refs) if entry_refs else 'NONE'))
lines.append('entry-8 value=0x%08X entry-4 value=0x%08X entry+4 value=0x%08X' % (u32(entry_rva-8), u32(entry_rva-4), u32(entry_rva+4)))
lines.append('CA8xxx slots: all in #1 .tp3 and values are image VAs 0x00A13xxx; entry: #6 .tp3, non-image sentinel 0x80000001.')
lines.append('Common instruction phenotype: FF15/FF25 absolute-memory form = HIGH.')
lines.append('Common table/provenance = LOW/UNKNOWN; common runtime role or RTTI relation = UNKNOWN.')
(OUT / 'high_reuse_slot_final_report.txt').write_text('\n'.join(lines), encoding='utf-8')

print('rows', len(rows), 'cfg_exact', sum(r['cfg_instruction_start']=='YES' for r in rows), 'candidate_low', sum(r['boundary_status']=='LINEAR_CANDIDATE_ONLY' for r in rows))
for slot in SLOTS:
    rs = [r for r in rows if r['slot_va'] == '0x%08X' % slot]
    print('slot 0x%08X value=0x%08X refs=%d ff15=%d ff25=%d cfg=%d' % (slot, slot_info[slot]['value'], len(rs), sum(r['opcode']=='FF15' for r in rs), sum(r['opcode']=='FF25' for r in rs), sum(r['cfg_instruction_start']=='YES' for r in rs)))
print('wrote', OUT / 'high_reuse_slot_final_refs.csv')
print('wrote', OUT / 'high_reuse_slot_final_report.txt')

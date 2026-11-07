import struct, collections, csv, hashlib
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

EXE = Path('codoMP_client_shipRetail.exe')
OUT = Path('scripts/_out')
IB = 0x400000
SLOTS = [0x00CA8114, 0x00CA8194, 0x00CA812C, 0x00CA819C, 0x00CA8164]
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
    if not s: return None
    q = rva - s['va']
    return s['pr'] + q if 0 <= q < s['rs'] else None

def off2rva(o):
    for s in SECS:
        if s['pr'] <= o < s['pr'] + s['rs']:
            return s['va'] + o - s['pr']
    return None

def u32(rva):
    o = off(rva)
    return struct.unpack_from('<I', D, o)[0] if o is not None and o + 4 <= len(D) else None

def is_exec(rva):
    s = sec_at(rva)
    return bool(s and s['name'] != '.tvm0' and (s['ch'] & 0x20000000) and off(rva) is not None)

def dirs():
    return opt + 96

def export_roots():
    er, es = struct.unpack_from('<II', D, dirs())
    if not er or not off(er): return [], []
    nf = u32(er + 24); af = u32(er + 28); nn = u32(er + 32); an = u32(er + 36)
    out = []
    for i in range(nf):
        r = u32(af + 4 * i)
        name = ''
        if i < nn:
            ao = off(an + 4 * i)
            if ao is not None: name = D[ao:].split(b'\0', 1)[0].decode('latin1')
        out.append((r, name))
    roots = [r for r, name in out if r is not None and is_exec(r)]
    return roots, out

def raw_refs():
    rows = []
    for s in SECS:
        if s['name'] == '.tvm0':
            continue
        b = D[s['pr']:s['pr'] + s['rs']]
        for j in range(len(b) - 6):
            if b[j] == 0xff and b[j+1] in (0x15, 0x25):
                slot = struct.unpack_from('<I', b, j + 2)[0]
                if slot in SLOTS:
                    rows.append(dict(rva=s['va'] + j, slot=slot, opcode=0x15 if b[j+1] == 0x15 else 0x25, raw=b[j:j+6].hex()))
    return sorted(rows, key=lambda x: (x['rva'], x['slot']))

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm(start, count=20, maxlen=0x800):
    o = off(start)
    s = sec_at(start)
    if o is None or not is_exec(start): return []
    lim = min(maxlen, len(D) - o, (s['vs'] - (start - s['va'])) if s else maxlen)
    return list(md.disasm(D[o:o+lim], IB + start, count=count))

# Candidate roots: exports + entry + direct E8 targets + strong prologues.
exp_roots, export_records = export_roots()
e8targets = collections.Counter()
e8refs = collections.defaultdict(list)
for s in SECS:
    if s['name'] == '.tvm0' or not (s['ch'] & 0x20000000): continue
    b = D[s['pr']:s['pr'] + s['rs']]
    for j in range(len(b) - 5):
        if b[j] == 0xe8:
            t = s['va'] + j + 5 + struct.unpack_from('<i', b, j + 1)[0]
            if is_exec(t):
                e8targets[t] += 1
                e8refs[t].append(s['va'] + j)

PROL = [b'\x55\x8b\xec', b'\x55\x89\xe5', b'\x8b\xff\x55\x8b\xec', b'\x64\xa1\x00\x00\x00\x00', b'\x6a\xff\x68', b'\x53\x8b\xdc']
prologue_starts = set()
for s in SECS:
    if s['name'] == '.tvm0' or not (s['ch'] & 0x20000000): continue
    b = D[s['pr']:s['pr'] + s['rs']]
    for p in PROL:
        pos = 0
        while True:
            q = b.find(p, pos)
            if q < 0: break
            prologue_starts.add(s['va'] + q)
            pos = q + 1
candidate_roots = set(exp_roots) | set(e8targets) | prologue_starts | {0x0e5dc690}

# Clean CFG from entry + exports. Tracks owning function root for reachable instruction starts.
cfg_owner = collections.defaultdict(set)
cfg_ins = {}
callees = collections.defaultdict(set)
queue = collections.deque((r, r) for r in sorted(set(exp_roots + [0x0e5dc690, 0x00036790, 0x000367a0])))
processed = set()
while queue:
    start, root = queue.popleft()
    key = (start, root)
    if key in processed or not is_exec(start): continue
    processed.add(key)
    for x in disasm(start, maxlen=0x10000):
        ins = x.address - IB
        cfg_ins[ins] = x
        cfg_owner[ins].add(root)
        m = x.mnemonic
        if m in ('ret', 'retn', 'iret', 'iretd', 'ud2', 'int3'): break
        if m == 'call':
            if x.operands and x.operands[0].type == CS_OP_IMM:
                t = x.operands[0].imm - IB
                if is_exec(t):
                    callees[root].add(t)
                    queue.append((t, t))
            continue
        if m.startswith('j'):
            if x.operands and x.operands[0].type == CS_OP_IMM:
                t = x.operands[0].imm - IB
                if is_exec(t): queue.append((t, root))
            if m == 'jmp': break

def linear_to(start, ref, limit=0x10000):
    if start > ref or not is_exec(start) or not is_exec(ref): return False, '', 0, None
    o = off(start); s = sec_at(start)
    if o is None: return False, 'no-map', 0, None
    lim = min(limit, len(D) - o, s['vs'] - (start - s['va']))
    pc = IB + start; n = 0; last = None
    for x in md.disasm(D[o:o+lim], IB + start):
        last = x
        if x.address == IB + ref: return True, 'reached', n, last
        if x.address > IB + ref: return False, 'passed', n, last
        n += 1
        if x.mnemonic in ('ret', 'retn', 'iret', 'iretd', 'ud2', 'int3'): return False, 'term:' + x.mnemonic, n, x
        if x.mnemonic == 'jmp': return False, 'term:jmp', n, x
    return False, 'end', n, last

def function_extent(start, maxlen=0x8000):
    o = off(start); s = sec_at(start)
    if o is None: return start, start, 'no-map', 0
    lim = min(maxlen, len(D) - o, s['vs'] - (start - s['va']))
    ins = list(md.disasm(D[o:o+lim], IB + start))
    if not ins: return start, start, 'no-insn', 0
    end = start
    reason = 'end'
    for x in ins:
        end = (x.address - IB) + x.size
        if x.mnemonic in ('ret', 'retn', 'iret', 'iretd', 'ud2', 'int3'):
            reason = 'ret/int'
            break
        if x.mnemonic == 'jmp':
            reason = 'jmp'
            break
    return start, end, reason, len(ins)

def choose_candidate(ref):
    owners = sorted(cfg_owner.get(ref, set()))
    if owners:
        root = owners[0]
        return root, 'CFG_EXACT', 'HIGH_CFG_STATIC', True, 'reached', 0
    candidates = []
    for st in candidate_roots:
        if st > ref or ref - st > 0x8000: continue
        s = sec_at(st); sr = sec_at(ref)
        if not s or not sr or s['i'] != sr['i']: continue
        ok, reason, n, last = linear_to(st, ref)
        if not ok: continue
        score = 0
        kind = []
        if st in e8targets:
            score += 8; kind.append('E8TARGET')
        if st in set(exp_roots):
            score += 10; kind.append('EXPORT')
        if st == 0x0e5dc690:
            score += 10; kind.append('ENTRY')
        if st in prologue_starts:
            score += 3; kind.append('PROLOGUE')
        candidates.append((score, st, '+'.join(kind) or 'START', reason, n))
    if not candidates:
        return None, 'NONE', 'UNKNOWN', False, 'none', 0
    candidates.sort(key=lambda z: (-z[0], -z[1]))
    score, st, kind, reason, n = candidates[0]
    conf = 'MEDIUM_E8_TARGET' if 'E8TARGET' in kind or 'EXPORT' in kind or 'ENTRY' in kind else 'LOW_PROLOGUE'
    return st, kind, conf, True, reason, n

refs = raw_refs()
by_slot = collections.defaultdict(list)
for x in refs: by_slot[x['slot']].append(x)
rows = []
for x in refs:
    rva = x['rva']
    val = u32(x['slot'] - IB)
    st, kind, conf, decok, reason, n = choose_candidate(rva)
    z = next(md.disasm(D[off(rva):off(rva)+16], IB + rva, count=1), None)
    if st is not None:
        fs, fe, freason, fcount = function_extent(st)
        fsize = fe - fs
    else:
        fs = fe = None; freason = ''; fsize = 0; fcount = 0
    rows.append(dict(ref_rva='0x%08X' % rva, slot='0x%08X' % x['slot'], slot_value='0x%08X' % val,
                     opcode='FF%02X' % x['opcode'], raw=x['raw'],
                     self_decode=(z.bytes.hex() if z else ''), self_text=(z.mnemonic + ' ' + z.op_str if z else ''),
                     cfg_reachable='YES' if rva in cfg_owner else 'NO',
                     cfg_roots=' '.join('0x%08X' % v for v in sorted(cfg_owner.get(rva, set()))),
                     candidate_func=('0x%08X' % st if st is not None else ''),
                     candidate_kind=kind, boundary_confidence=conf,
                     decode_to_ref='YES' if decok else 'NO', decode_reason=reason, decode_insn_count=str(n),
                     func_start=('0x%08X' % fs if fs is not None else ''),
                     func_end_linear=('0x%08X' % fe if fe is not None else ''),
                     func_size=('0x%X' % fsize if fs is not None else ''), func_end_reason=freason,
                     func_decode_insns=str(fcount),
                     direct_e8_callers=' '.join('0x%08X' % v for v in sorted(set(e8refs.get(st, [])))) if st is not None else '',
                     direct_e8_caller_count=str(len(set(e8refs.get(st, [])))) if st is not None else '0',
                     pre64=D[max(0, off(rva)-64):off(rva)].hex(),
                     post64=D[off(rva)+6:min(len(D), off(rva)+70)].hex()))

with (OUT / 'high_reuse_slot_detail.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# Detailed text, grouped by slot. Context disassembly is from candidate function when it linearly reaches ref, otherwise self.
with (OUT / 'high_reuse_slot_disasm.txt').open('w', encoding='utf-8') as f:
    f.write('High-reuse CA8xxx slot caller boundary/detail audit\n')
    f.write('Input SHA256 %s\n' % hashlib.sha256(D).hexdigest())
    f.write('Raw refs=%d; CFG exact=%d; candidate boundary=%d\n\n' % (len(rows), sum(r['cfg_reachable']=='YES' for r in rows), sum(r['candidate_func']!='' for r in rows)))
    for slot in SLOTS:
        rs = [r for r in rows if r['slot'] == '0x%08X' % slot]
        f.write('=' * 100 + '\nSLOT 0x%08X value=0x%08X raw_refs=%d FF15=%d FF25=%d\n' % (slot, u32(slot - IB), len(rs), sum(r['opcode']=='FF15' for r in rs), sum(r['opcode']=='FF25' for r in rs)))
        for r in rs:
            f.write('-' * 100 + '\nREF %s opcode=%s raw=%s self=%s\n' % (r['ref_rva'], r['opcode'], r['raw'], r['self_text']))
            f.write('cfg=%s roots=%s candidate=%s kind=%s conf=%s decode=%s/%s/%s\n' % (r['cfg_reachable'], r['cfg_roots'] or '-', r['candidate_func'] or '-', r['candidate_kind'], r['boundary_confidence'], r['decode_to_ref'], r['decode_reason'], r['decode_insn_count']))
            f.write('candidate extent=%s..%s size=%s end=%s insns=%s direct_e8_callers=%s [%s]\n' % (r['func_start'] or '-', r['func_end_linear'] or '-', r['func_size'] or '-', r['func_end_reason'] or '-', r['func_decode_insns'], r['direct_e8_caller_count'], r['direct_e8_callers'] or '-'))
            rv = int(r['ref_rva'], 16)
            if r['candidate_func'] and r['decode_to_ref'] == 'YES':
                allins = list(md.disasm(D[off(int(r['candidate_func'],16)):off(rv)+16], IB + int(r['candidate_func'],16)))
                for z in allins:
                    if IB + rv - 64 <= z.address <= IB + rv + 16:
                        mark = ' <== REF' if z.address - IB == rv else ''
                        f.write('  %08X  %-24s %s%s\n' % (z.address - IB, z.bytes.hex(), z.mnemonic + ' ' + z.op_str, mark))
            else:
                f.write('  BYTES[-64:+70] %s %s %s\n' % (r['pre64'], r['raw'], r['post64']))
                for z in disasm(rv, count=12):
                    mark = ' <== REF' if z.address - IB == rv else ''
                    f.write('  %08X  %-24s %s%s\n' % (z.address - IB, z.bytes.hex(), z.mnemonic + ' ' + z.op_str, mark))
        f.write('\n')

# Local co-reference relationships among the five slots within 64 bytes.
co = []
for a in refs:
    for b in refs:
        if b['rva'] <= a['rva'] or b['rva'] - a['rva'] > 64: continue
        co.append((a['rva'], a['slot'], b['rva'], b['slot'], b['rva'] - a['rva'], b['opcode']))
with (OUT / 'high_reuse_slot_coref.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['left_rva','left_slot','right_rva','right_slot','delta','right_opcode']); w.writerows(co)

# Group candidate functions to look for shared upper callers among refs.
func_groups = collections.defaultdict(list)
for r in rows:
    if r['candidate_func']: func_groups[r['candidate_func']].append(r)
with (OUT / 'high_reuse_slot_function_groups.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['candidate_func','ref_count','refs','direct_e8_callers','cfg_exact_count'])
    for fn, rs in sorted(func_groups.items()):
        w.writerow([fn, len(rs), ' '.join(r['ref_rva'] for r in rs), ' '.join(sorted({c for r in rs for c in r['direct_e8_callers'].split() if c})), sum(r['cfg_reachable']=='YES' for r in rs)])

# Summaries.
lines = []
lines.append('HIGH-REUSE SLOT CALLER CLUSTER SUMMARY')
lines.append('raw_refs=%d ff15=%d ff25=%d' % (len(rows), sum(r['opcode']=='FF15' for r in rows), sum(r['opcode']=='FF25' for r in rows)))
lines.append('self_decode_ok=%d cfg_exact=%d candidate_linear=%d unresolved=%d' % (sum(bool(r['self_decode']) for r in rows), sum(r['cfg_reachable']=='YES' for r in rows), sum(r['candidate_func']!='' for r in rows), sum(r['candidate_func']=='' for r in rows)))
lines.append('co_ref_pairs_le64=%d' % len(co))
lines.append('')
for slot in SLOTS:
    rs = [r for r in rows if r['slot'] == '0x%08X' % slot]
    lines.append('SLOT 0x%08X value=0x%08X refs=%d FF15=%d FF25=%d' % (slot, u32(slot - IB), len(rs), sum(r['opcode']=='FF15' for r in rs), sum(r['opcode']=='FF25' for r in rs)))
    lines.append('  cfg_exact=' + ', '.join(r['ref_rva'] for r in rs if r['cfg_reachable']=='YES'))
    lines.append('  candidate_boundaries=' + ', '.join(r['ref_rva'] + '/' + r['candidate_func'] + '/' + r['boundary_confidence'] for r in rs if r['candidate_func']))
    lines.append('  unresolved=' + ' '.join(r['ref_rva'] for r in rs if not r['candidate_func']))
    lines.append('')
lines.append('CO-REF <=64')
for x in co:
    lines.append('  %08X[%08X] -> %08X[%08X] delta=+%d op=%s' % (x[0], x[1], x[2], x[3], x[4], x[5]))
lines.append('')
lines.append('FUNCTION GROUPS')
for fn, rs in sorted(func_groups.items()):
    lines.append('  0x%s refs=%s callers=%s exact=%s' % (fn[2:], ' '.join(r['ref_rva'] for r in rs), ' '.join(sorted({c for r in rs for c in r['direct_e8_callers'].split() if c})) or '-', sum(r['cfg_reachable']=='YES' for r in rs)))
(OUT / 'high_reuse_slot_cluster_summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))

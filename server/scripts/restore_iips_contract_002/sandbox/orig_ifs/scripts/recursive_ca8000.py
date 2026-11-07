import struct, collections
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

P = Path(r"codoMP_client_shipRetail.exe")
D = P.read_bytes()
IB = 0x400000
SECS = [
    (0, '.tp3', 0x00001000, 0x08A689A, 0x001000, 0x593000, 0x60000020),
    (1, '.tp3', 0x008A8000, 0x016DA70, 0x594000, 0x16E000, 0x40000040),
    (2, '.tp3', 0x00A16000, 0xDBB1CC0, 0x702000, 0x062000, 0xC0000040),
    (3, '.tp3', 0x0E5C8000, 0x0000031, 0x764000, 0x001000, 0xC0000040),
    (4, '.tp3', 0x0E5C9000, 0x0009228, 0x765000, 0x00A000, 0x40000040),
    (5, '.tvm0', 0x0E5D3000, 0x0004000, 0x76F000, 0x002000, 0x60000020),
    (6, '.tp3', 0x0E5D7000, 0x0082000, 0x771000, 0x006000, 0xE0000020),
]

def sec_of(rva):
    for s in SECS:
        if s[2] <= rva < s[2] + max(s[3], s[5]):
            return s
    return None

def r2o(rva):
    s = sec_of(rva)
    if not s:
        return None
    x = rva - s[2]
    return s[4] + x if 0 <= x < s[5] else None

def executable(rva):
    s = sec_of(rva)
    return bool(s and (s[6] & 0x20000000))

def traverse(md, insmap, seen, todo, events, unresolved):
    fn = todo.popleft()
    if fn in seen or not executable(fn):
        return
    seen.add(fn)
    rva = fn
    for _ in range(200000):
        if not executable(rva) or rva in insmap:
            return
        off = r2o(rva)
        if off is None:
            return
        ins = next(md.disasm(D[off:off + 15], IB + rva, count=1), None)
        if ins is None:
            return
        insmap[rva] = ins
        ops = ins.operands
        mn = ins.mnemonic
        flow = 'fall'
        if mn == 'call':
            if ops and ops[0].type == X86_OP_IMM and ops[0].imm is not None:
                t = int(ops[0].imm) - IB
                if executable(t):
                    todo.append(t)
            elif ops and ops[0].type == X86_OP_MEM:
                m = ops[0].mem
                if m.base == 0 and m.index == 0 and m.disp is not None:
                    opv = int(m.disp)
                    if 0xCA8000 <= opv < 0xCA8800:
                        events.append((rva, opv, ins.bytes.hex(), mn, ins.op_str, 'abs_table'))
                    else:
                        events.append((rva, opv, ins.bytes.hex(), mn, ins.op_str, 'abs_other'))
                else:
                    unresolved['call_mem_nonabs'] += 1
            else:
                unresolved['call_reg'] += 1
        elif mn == 'jmp':
            flow = 'stop'
            if ops and ops[0].type == X86_OP_IMM and ops[0].imm is not None:
                t = int(ops[0].imm) - IB
                if executable(t):
                    todo.append(t)
            elif ops and ops[0].type == X86_OP_MEM:
                m = ops[0].mem
                if m.base == 0 and m.index == 0 and m.disp is not None:
                    opv = int(m.disp)
                    if 0xCA8000 <= opv < 0xCA8800:
                        events.append((rva, opv, ins.bytes.hex(), mn, ins.op_str, 'abs_table'))
                    else:
                        events.append((rva, opv, ins.bytes.hex(), mn, ins.op_str, 'abs_other'))
                else:
                    unresolved['jmp_mem_nonabs'] += 1
            else:
                unresolved['jmp_reg'] += 1
        elif mn.startswith('j') and mn != 'jmp':
            if ops and ops[0].type == X86_OP_IMM and ops[0].imm is not None:
                t = int(ops[0].imm) - IB
                if executable(t):
                    todo.append(t)
        elif mn in ('ret', 'retf', 'iret', 'iretq', 'hlt', 'ud2', 'int3'):
            flow = 'stop'
        if flow == 'stop':
            return
        rva += int(ins.size)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
insmap = {}
seen = set()
todo = collections.deque([0x0E5DC690])
events = []
unresolved = collections.Counter()
while todo:
    traverse(md, insmap, seen, todo, events, unresolved)

# Add direct-call candidate seeds. This deliberately over-seeds; later matching only counts
# candidate byte positions that are actual instruction starts in the resulting map.
new = 0
for _, _, va, _, rawptr, rawsz, chars in SECS:
    if not (chars & 0x20000000):
        continue
    b = D[rawptr:rawptr + rawsz]
    for k in range(len(b) - 4):
        if b[k] == 0xE8:
            rel = struct.unpack_from('<i', b, k + 1)[0]
            t = va + k + 5 + rel
            if executable(t) and t not in seen:
                todo.append(t)
                new += 1
while todo:
    traverse(md, insmap, seen, todo, events, unresolved)

tableevents = [e for e in events if e[-1] == 'abs_table']
print('direct_seed_candidates', new, 'functions', len(seen), 'instructions', len(insmap))
print('collected_abs_events', len(events), 'table', len(tableevents), 'other', len(events)-len(tableevents))
print('table_opcodes', dict(collections.Counter(e[3] for e in tableevents)))
print('table_slots', len(set(e[1] for e in tableevents)))
print('top_slots', [(hex(k), v) for k, v in collections.Counter(e[1] for e in tableevents).most_common(40)])

raw = []
for off in range(len(D) - 5):
    if D[off] == 0xFF and D[off + 1] in (0x15, 0x25):
        op = struct.unpack_from('<I', D, off + 2)[0]
        if 0xCA8000 <= op < 0xCA8800:
            r = None
            for _, _, va, _, rawptr, rawsz, _ in SECS:
                if rawptr <= off < rawptr + rawsz:
                    r = va + off - rawptr
                    break
            raw.append((r, op, off, D[off + 1]))

valid = []
invalid = []
unmapped = []
for r, op, off, opc in raw:
    if r is None:
        unmapped.append((r, op, off, opc))
        continue
    ins = insmap.get(r)
    good = False
    if ins:
        ops = ins.operands
        good = ((ins.mnemonic == 'call' and opc == 0x15) or (ins.mnemonic == 'jmp' and opc == 0x25)) and ops and ops[0].type == X86_OP_MEM and ops[0].mem.base == 0 and ops[0].mem.index == 0 and int(ops[0].mem.disp) == op
    if good:
        valid.append((r, op, off, opc))
    else:
        invalid.append((r, op, off, opc, ins.mnemonic if ins else None, ins.op_str if ins else None))
print('raw', len(raw), 'valid', len(valid), 'valid_slots', len(set(x[1] for x in valid)), 'invalid', len(invalid), 'unmapped', len(unmapped))
print('valid_opcodes', dict(collections.Counter('FF%02X' % x[3] for x in valid)))
print('valid_top', [(hex(k), v) for k, v in collections.Counter(x[1] for x in valid).most_common(50)])
print('invalid_first', [(hex(r), hex(op), hex(off), hex(opc), mn, ops) for r, op, off, opc, mn, ops in invalid[:100]])

out = Path(r"scripts/_out/ca8000_recursive.txt")
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w', encoding='utf-8') as f:
    f.write('direct_seed_candidates=%d functions=%d instructions=%d\n' % (new, len(seen), len(insmap)))
    f.write('raw=%d valid=%d valid_slots=%d invalid=%d unmapped=%d\n' % (len(raw), len(valid), len(set(x[1] for x in valid)), len(invalid), len(unmapped)))
    f.write('valid_slot,count\n')
    for k, v in sorted(collections.Counter(x[1] for x in valid).items()):
        f.write('%08X,%d\n' % (k, v))
    f.write('\ninvalid\n')
    for z in invalid:
        f.write(','.join('' if x is None else str(x) for x in z) + '\n')
print('report', out)
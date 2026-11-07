# -*- coding: utf-8 -*-
"""Instruction-level references to the 0xCA8000 slot region.

Read-only.  Seeds recursive decoding from every E8 rel32 candidate (deliberately
over-inclusive), then accepts a reference only when the candidate byte offset is
an instruction start in that map.  This separates data coincidences from code.
"""
import struct, collections, pathlib, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_AC_READ, CS_AC_WRITE
from capstone.x86 import X86_OP_MEM

D = pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes()
IB = 0x400000
SOI = 0x0E659000
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
        if s[2] <= rva < s[2] + max(s[3], s[5]): return s
    return None

def r2o(rva):
    s = sec_of(rva)
    if not s: return None
    x = rva - s[2]
    return s[4] + x if 0 <= x < s[5] else None

def exec_at(rva):
    s = sec_of(rva)
    return bool(s and (s[6] & 0x20000000))

def hx(x): return '0x%08X' % x

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def one(rva):
    o = r2o(rva)
    if o is None: return None
    return next(md.disasm(D[o:o+15], IB + rva, count=1), None)

def traverse(fn, insmap, seen, todo):
    if fn in seen or not exec_at(fn): return
    seen.add(fn)
    rva = fn
    for _ in range(200000):
        if not exec_at(rva) or rva in insmap: return
        ins = one(rva)
        if ins is None: return
        insmap[rva] = ins
        ops = ins.operands; mn = ins.mnemonic
        if mn == 'call':
            if ops and ops[0].type == 2 and ops[0].imm is not None:  # X86_OP_IMM
                t = int(ops[0].imm) - IB
                if exec_at(t): todo.append(t)
        elif mn == 'jmp':
            if ops and ops[0].type == 2 and ops[0].imm is not None:
                t = int(ops[0].imm) - IB
                if exec_at(t): todo.append(t)
            return
        elif mn.startswith('j') and ops and ops[0].type == 2 and ops[0].imm is not None:
            t = int(ops[0].imm) - IB
            if exec_at(t): todo.append(t)
        elif mn in ('ret','retf','iret','iretq','hlt','ud2','int3'):
            return
        rva += int(ins.size)

insmap = {}; seen = set(); todo = collections.deque([0x0E5DC690])
while todo: traverse(todo.popleft(), insmap, seen, todo)
seed_n = 0
for _,_,va,_,rawptr,rawsz,ch in SECS:
    if not (ch & 0x20000000): continue
    b = D[rawptr:rawptr+rawsz]
    for k in range(len(b)-4):
        if b[k] == 0xE8:
            t = va + k + 5 + struct.unpack_from('<i', b, k+1)[0]
            if exec_at(t) and t not in seen:
                todo.append(t); seed_n += 1
while todo: traverse(todo.popleft(), insmap, seen, todo)

BASE, LIM = 0x00CA8000, 0x00CA875C
refs = []
for rva, ins in insmap.items():
    for oi, op in enumerate(ins.operands):
        if op.type != X86_OP_MEM: continue
        m = op.mem
        if m.base != 0 or m.index != 0: continue
        if not (BASE <= int(m.disp) <= LIM): continue
        if ins.mnemonic == 'lea':
            effect = 'ADDR'
        else:
            a = int(op.access)
            rd = bool(a & CS_AC_READ); wr = bool(a & CS_AC_WRITE)
            effect = 'RMW' if rd and wr else ('WRITE' if wr else ('READ' if rd else 'NONE'))
        refs.append((rva, int(m.disp), ins.mnemonic, ins.op_str, ins.bytes.hex(), effect, oi))

# de-duplicate (same instruction could expose same disp twice only in weird encodings)
refs = list(dict.fromkeys(refs))
by = collections.defaultdict(list)
for x in refs: by[x[1]].append(x)

def cls(v):
    if v == 0: return 'ZERO'
    if 0x80000000 <= v <= 0x8fffffff: return 'SENT'
    if IB <= v < IB+SOI: return 'PTR'
    return 'OTHER'

rows = []
for i in range((LIM-BASE)//4 + 1):
    slot = BASE + 4*i; v = struct.unpack_from('<I', D, r2o(slot-IB))[0]
    r = v-IB if IB <= v < IB+SOI else None
    s = sec_of(r) if r is not None else None
    rs = by.get(slot, [])
    rows.append(dict(i=i,slot=slot,value=v,target_rva=r,target_sec=('%s#%d'%(s[1],s[0]) if s else None),
                     target_raw=bool(s and r2o(r) is not None), cls=cls(v),
                     refs=rs, nrefs=len(rs),
                     reads=sum(x[5]=='READ' for x in rs), writes=sum(x[5]=='WRITE' for x in rs),
                     rmw=sum(x[5]=='RMW' for x in rs), addr=sum(x[5]=='ADDR' for x in rs),
                     call=sum(x[2] in ('call','jmp') for x in rs),
                     mov=sum(x[2]=='mov' for x in rs)))

outdir = pathlib.Path('scripts/_out'); outdir.mkdir(parents=True, exist_ok=True)
# CSV
with (outdir/'ca8000_semantic_slots.csv').open('w', encoding='utf-8', newline='') as f:
    f.write('index,slot,value,target_rva,target_section,target_raw_backed,class,nrefs,reads,writes,rmw,addr,call,mov\n')
    for x in rows:
        f.write('%d,0x%08X,0x%08X,%s,%s,%d,%s,%d,%d,%d,%d,%d,%d,%d\n' % (
            x['i'],x['slot'],x['value'],hx(x['target_rva']) if x['target_rva'] is not None else '',
            x['target_sec'] or '', int(x['target_raw']),x['cls'],x['nrefs'],x['reads'],x['writes'],x['rmw'],x['addr'],x['call'],x['mov']))
# full refs CSV
with (outdir/'ca8000_semantic_refs.csv').open('w', encoding='utf-8', newline='') as f:
    f.write('caller_rva,slot,mnemonic,op_str,bytes,effect,operand_index\n')
    for x in sorted(refs): f.write('0x%08X,0x%08X,%s,"%s",%s,%s,%d\n'%(x[0],x[1],x[2],x[3],x[4],x[5],x[6]))

print('INSTRUCTION_MAP functions=%d instructions=%d direct_E8_seeds=%d' % (len(seen),len(insmap),seed_n))
print('VALID_REFS total=%d distinct_slots=%d' % (len(refs),len(by)))
print('EFFECTS',dict(collections.Counter(x[5] for x in refs)))
print('MNEMONICS',collections.Counter(x[2] for x in refs).most_common())
print('WRITE_REFS',[(hx(x[0]),hx(x[1]),x[2],x[3],x[5]) for x in refs if x[5] in ('WRITE','RMW')])
print('ADDR_REFS',[(hx(x[0]),hx(x[1]),x[2],x[3]) for x in refs if x[5]=='ADDR'])
print('CALL_REFS',[(hx(x[0]),hx(x[1]),x[2]) for x in refs if x[2] in ('call','jmp')])
print('SLOT_CLASSES_ALL',dict(collections.Counter(x['cls'] for x in rows)))
print('REFERENCED_CLASSES',dict(collections.Counter(x['cls'] for x in rows if x['nrefs'])))
print('TOP_SLOTS')
for x in sorted(rows,key=lambda z:(-z['nrefs'],z['slot']))[:60]:
    print('  %s value=%s cls=%s refs=%d(read=%d write=%d rmw=%d addr=%d call=%d)' % (hx(x['slot']),hx(x['value']),x['cls'],x['nrefs'],x['reads'],x['writes'],x['rmw'],x['addr'],x['call']))
print('SENTINEL_SLOTS')
for x in rows:
    if x['cls']=='SENT':
        print('  %s %s refs=%d call=%d reads=%d writes=%d addr=%d' % (hx(x['slot']),hx(x['value']),x['nrefs'],x['call'],x['reads'],x['writes'],x['addr']))

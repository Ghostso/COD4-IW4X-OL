# -*- coding: utf-8 -*-
"""scanrw.py VALUE -- 逐个引用点判定 读/写：对每个 4 字节值出现处，从指令起点反汇编一小段，
报告后续是否有对 +0xC 的 store。用法: python -I scanrw.py 0x1C2B064 [n]"""
import sys, io, struct
HERE = __file__.rsplit('\\', 1)[0]
sys.path.insert(0, HERE)
from verify import P, MD, insns

val = int(sys.argv[1], 16)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
need = struct.pack('<I', val)

out = []
hits = []
for v, vs, ra, rs, ch in P.secs:
    if not (ch & 0x20000000):
        continue
    buf = P.d[ra:ra + min(vs, rs)]
    i = 0
    while True:
        j = buf.find(need, i)
        if j < 0:
            break
        hits.append(v + j)
        i = j + 1

out.append('value 0x%X  exec-hits=%d' % (val, len(hits)))
reads = writes = other = 0
for h in hits:
    # 指令起点：在命中点前 1..8 字节里挑**唯一**能把该值当作操作数的解码
    #   （避免 00 A1 … 之类重叠前缀把 A1 … 遮掉）
    vkey = '0x%x' % val
    best = None
    for st in range(h - 1, h - 9, -1):
        b = P.rd(st, 12)
        if not b:
            continue
        try:
            ds = list(MD.disasm(b, st, count=1))
        except Exception:
            continue
        if not ds or ds[0].address + ds[0].size != h + 4:
            continue
        t = ds[0].mnemonic + ' ' + ds[0].op_str
        if ('[%s]' % vkey) in t or ('+ %s]' % vkey) in t or ('- %s]' % vkey) in t:
            best = st
            break
    if best is None:
        out.append('  %08X  <未定位指令起点>' % h)
        other += 1
        continue
    seq = insns(best, n)
    txt = ' | '.join(seq)
    head = seq[0] if seq else ''
    # 判定：命中指令自身是否把该位移当作**目的操作数**（写）
    #   写形态： 'mov byte ptr [reg + 0xc], al'  /  'mov dword ptr [reg + 0xc], eax'
    #   读形态： 操作数里 [reg + 0xc] 出现在逗号**之前**
    isw2 = False
    if ',' in head:
        dst, src = head.split(',', 1)
        if ('[' in dst and ']' in dst) and ('ptr [' in dst):
            isw2 = True
    if isw2:
        writes += 1
        tag = 'WRITE!'
    else:
        reads += 1
        tag = 'read  '
    out.append('  %-7s %08X  %s' % (tag, best, txt))
out.append('--- reads=%d writes=%d other=%d ---' % (reads, writes, other))
txt = '\n'.join(out)
io.open(HERE + '\\out\\scanrw.txt', 'w', encoding='utf-8').write(txt + '\n')
sys.stdout.write(txt.encode('ascii', 'backslashreplace').decode('ascii') + '\n')

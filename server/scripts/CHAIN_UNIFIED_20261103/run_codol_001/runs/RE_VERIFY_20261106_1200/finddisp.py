# -*- coding: utf-8 -*-
"""finddisp.py VALUE [--win N] -- 在可执行段逐字节找 4 字节小端值，并在每个命中处反汇编上下文"""
import sys, io
HERE = __file__.rsplit('\\', 1)[0]
sys.path.insert(0, HERE)
from verify import P, MD, xrefs, insns

val = int(sys.argv[1], 16)
win = 6
if '--win' in sys.argv:
    win = int(sys.argv[sys.argv.index('--win') + 1])

out = []
hits = xrefs(val)
out.append('value 0x%X  hits=%d' % (val, len(hits)))
for h in hits:
    out.append('--- hit @%08X ---' % h)
    start = h - 15
    buf = P.rd(start, 40)
    pend = []
    for ins in MD.disasm(buf, start):
        mark = '  <<<' if ins.address <= h < ins.address + ins.size else ''
        pend.append('  %08X  %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, mark))
    # 只保留命中前后各 win 条
    idx = [i for i, l in enumerate(pend) if '<<<' in l]
    if idx:
        i0 = max(0, idx[0] - win); i1 = min(len(pend), idx[0] + win + 1)
        out.extend(pend[i0:i1])
io.open(HERE + '\\out\\finddisp.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
sys.stdout.write('\n'.join(out).encode('ascii', 'backslashreplace').decode('ascii') + '\n')

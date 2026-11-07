# -*- coding: utf-8 -*-
"""fnstart.py VA -- 从 VA 向前找最近的 CC 填充，返回函数入口候选，并从该处反汇编"""
import sys, io
HERE = __file__.rsplit('\\', 1)[0]
sys.path.insert(0, HERE)
from verify import P, MD

va = int(sys.argv[1], 16)
# 向前找 4 个连续 0xCC
start = None
for s in range(va - 1, va - 0x2000, -1):
    b = P.rd(s - 3, 4)
    if b == b'\xcc\xcc\xcc\xcc':
        start = s
        break
out = []
out.append('fn_start candidate = %08X' % (start or 0))
if start:
    buf = P.rd(start, 16 * 200)
    for ins in MD.disasm(buf, start):
        out.append('%08X  %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str,
                                        '   <<< target' if ins.address <= va < ins.address + ins.size else ''))
        if ins.address > va + 0x120:
            break
io.open(HERE + '\\out\\fn.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
sys.stdout.write('\n'.join(out).encode('ascii', 'backslashreplace').decode('ascii') + '\n')

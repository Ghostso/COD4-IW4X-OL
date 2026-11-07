# -*- coding: utf-8 -*-
"""dumpm.py VA [N] -- 反汇编 N 条指令（默认 40）"""
import sys, io
sys.path.insert(0, __file__.rsplit('\\',1)[0])
from verify import P, MD, insns
a = int(sys.argv[1], 16)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
out = []
buf = P.rd(a, 16*n)
for ins in MD.disasm(buf, a):
    out.append('%08X  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
    if len(out) >= n: break
io.open(__file__.rsplit('\\',1)[0] + '\\out\\dump.txt','w',encoding='utf-8').write('\n'.join(out)+'\n')
sys.stdout.write('\n'.join(out).encode('ascii','backslashreplace').decode('ascii')+'\n')

"""函数内 esp 线性跟踪 + 栈槽归一化（只读）。

把 [esp+X] 归一化成「相对函数入口 esp 的偏移 F」，消除 push/pop 造成的漂移。
capstone 对小位移输出十进制、大位移输出 0x 十六进制 —— 两种都要认。
call dword ptr [slot]（stdcall）不知清栈量，标 STD?；若紧跟 add esp,N 且与
其前 push 数吻合，则跟踪可信（脚本末尾自动核对）。
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
img = Image()
RE_ESP = re.compile(r'\[esp(?: ([+-]) (0x[0-9a-f]+|\d+))?\]')

def run(lo, hi, tag):
    print('=' * 84); print('### %s  [0x%08x, 0x%08x]   归一化 = 相对入口 esp 的偏移' % (tag, lo, hi)); print('=' * 84)
    d = 0
    for ins in X.dis(img, lo, hi - lo):
        mn, op = ins.mnemonic, ins.op_str
        pre = d
        if mn == 'sub' and op.startswith('esp, '):
            d -= int(op.split(', ')[1], 0)
        elif mn == 'add' and op.startswith('esp, '):
            d += int(op.split(', ')[1], 0)
        elif mn == 'push': d -= 4
        elif mn == 'pop':  d += 4
        def sub_m(m):
            x = int(m.group(2), 0) if m.group(2) else 0
            if m.group(1) == '-': x = -x
            return '[F%+#x]' % (pre + x)
        if 'esp' in op:
            op = RE_ESP.sub(sub_m, op)
        note = ''
        if mn.startswith('call') and '[0x' in op: note = '  <STDCALL?>'
        elif mn == 'call' and op.startswith('0x'): note = '  (内部)'
        print('  %08x  %-10s %-11s %s%s' % (ins.address, 'd=%+#x' % d, mn, op, note))

import sys as _s
run(int(_s.argv[1], 0), int(_s.argv[2], 0), ' '.join(_s.argv[3:]) or 'dump')

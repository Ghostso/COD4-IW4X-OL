"""CFG 感知的 esp 跟踪（只读）。

基本块工作队列：jcc 把 d 同时传给落空与目标，jmp 只传目标，ret 终止。
栈记账：
  push      -> d -= 4, pend += 4
  pop       -> d += 4
  add esp,N -> 核对 pend == N（不等则打 !!，说明前面的调用约定猜错）；d += N; pend = 0
  call rel32(内部/cdecl) -> d 不变; pend = 0（调用者负责 add esp）
  call [slot](Win32 stdcall) -> d += pend; pend = 0
输出 raw 位移与归一化 F 偏移。用法:
   python scripts/esptrack2.py <lo> <hi> [base] [tag]
"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
img = Image()
RE_ESP = re.compile(r'\[esp(?: ([+-]) (0x[0-9a-f]+|\d+))?\]')

lo, hi = int(sys.argv[1], 0), int(sys.argv[2], 0)
base = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
tag = ' '.join(sys.argv[4:]) or 'dump'

insns = {i.address: i for i in X.dis(img, lo, hi - lo)}
COND = set('je jne jz jnz jg jge jl jle ja jae jb jbe js jns jo jno jp jnp jecxz'
           .split())

state = {}
warn = []
q = collections.deque([(lo, base)])
while q:
    a, d = q.popleft()
    pend = 0
    while True:
        if a not in insns or a in state:
            break
        state[a] = d
        ins = insns[a]
        mn, op = ins.mnemonic, ins.op_str
        nxt = a + ins.size
        if mn == 'ret':
            break
        if mn == 'jmp' and op.startswith('0x'):
            a = int(op, 16)
            continue
        if mn in COND and op.startswith('0x'):
            q.append((int(op, 16), d))
            a = nxt
            continue
        if mn == 'call':
            if '[0x' in op:            # Win32 stdcall: 自己清 args
                if d is not None:
                    d += pend
                pend = 0
            # 内部 cdecl: pend 保留, 等调用者的 add esp,N 对账
        elif mn == 'push':
            if d is not None:
                d -= 4
            pend += 4
        elif mn == 'pop':
            if d is not None:
                d += 4
        elif mn in ('add', 'sub') and op.startswith('esp, '):
            n = int(op.split(', ')[1], 0)
            if mn == 'add':
                if n != pend:
                    warn.append('  !! %08x: add esp,0x%x 但累计 push 只有 0x%x'
                                % (a, n, pend))
                if d is not None:
                    d += n
            else:
                if d is not None:
                    d -= n
            pend = 0
        a = nxt

print('### %s   [0x%08x, 0x%08x]  base=%+#x' % (tag, lo, hi, base))
print('### d = esp 相对 base 的位移；F 偏移 = 相对本块基址')
print('-' * 88)
for a in sorted(state):
    d = state[a]
    ins = insns[a]
    mn, op = ins.mnemonic, ins.op_str
    box = ['']
    def sub_m(m):
        x = int(m.group(2), 0) if m.group(2) else 0
        if m.group(1) == '-':
            x = -x
        box[0] = '%+#x' % x
        return '[F%+#x]' % (d + x) if d is not None else '[?%+#x]' % x
    if 'esp' in op:
        op = RE_ESP.sub(sub_m, op)
    print('  %08x  d=%-8s  %-10s %-44s %s' % (
        a, ('%+#x' % d) if d is not None else 'None', mn, op, 'raw esp%s' % box[0] if box[0] else ''))
for w in warn:
    print(w)

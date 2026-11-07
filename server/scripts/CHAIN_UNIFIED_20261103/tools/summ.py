"""批量函数摘要器 —— 一次给出多个函数的结构画像。

对每个地址输出:
  - 入口 / 大小 / 指令数
  - WRITES : 出现过的 [reg+disp] 写偏移（按出现顺序去重）→ 用来判断"它写了哪些字段"
  - CALLS  : 直接调用目标（去重，按出现顺序）
  - COND   : cmp/test 的操作数（去重，前 12 个）→ 用来判断判据
  - TAIL   : 末尾若干条指令（判断是 ret 还是尾调用）

用法: python -I summ.py 0xBB1920 0xBB3940 0xBB3B00 ...
      python -I summ.py --full 0xBB1920      # 额外打印全部指令
"""
import sys, struct, bisect
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d = open(P, 'rb').read()

e = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, e + 6)[0]
opt = struct.unpack_from('<H', d, e + 20)[0]
ib = struct.unpack_from('<I', d, e + 52)[0]
s0 = e + 24 + opt
SECS = []
for k in range(nsec):
    p = s0 + 40 * k
    vs, va, rs, ra = struct.unpack_from('<IIII', d, p + 8)
    ch = struct.unpack_from('<I', d, p + 36)[0]
    SECS.append((ib + va, vs, ra, rs, bool(ch & 0x20000000)))
EXEC = [s for s in SECS if s[4]]


def sec_of(va):
    for s in SECS:
        if s[0] <= va < s[0] + max(s[1], s[3]):
            return s
    return None


def in_exec(va):
    s = sec_of(va)
    return bool(s and s[4])


def rd(va, n):
    s = sec_of(va)
    if not s:
        return None
    o = s[2] + (va - s[0])
    if o < 0 or o + n > len(d):
        return None
    return d[o:o + n]


# ---- 入口表（E8 目标 ∪ SEH 序言），与 graph.py 一致 ----
entries = set()
for s in EXEC:
    blob = d[s[2]:s[2] + min(max(s[1], s[3]), len(d) - s[2])]
    base = s[0]
    i = blob.find(b'\xe8')
    while i >= 0:
        if i + 5 <= len(blob):
            rel = struct.unpack_from('<i', blob, i + 1)[0]
            t = (base + i + 5 + rel) & 0xFFFFFFFF
            if in_exec(t):
                entries.add(t)
        i = blob.find(b'\xe8', i + 1)
    j = blob.find(b'\x55\x8b\xec\x6a\xff\x68')
    while j >= 0:
        entries.add(base + j)
        j = blob.find(b'\x55\x8b\xec\x6a\xff\x68', j + 1)
ENT = sorted(entries)


def size_of(va):
    k = bisect.bisect_right(ENT, va)
    return (ENT[k] - va) if k < len(ENT) else 0x400


md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False


def summarize(va, full=False):
    sz = min(size_of(va) or 0x400, 0x1000)
    code = rd(va, sz)
    if not code:
        print('  0x%08X 无法读取' % va); return
    insns = list(md.disasm(code, va))
    writes, calls, conds = [], [], []
    for ins in insns:
        ops = ins.op_str
        # 写操作：目标以 [ 开头
        if ins.mnemonic in ('mov', 'movzx', 'movsx', 'or', 'and', 'xor', 'add', 'sub'):
            if ops.startswith('dword ptr [') or ops.startswith('word ptr [') or ops.startswith('byte ptr ['):
                tgt = ops.split(',')[0]
                tgt = tgt.replace('dword ptr ', '').replace('word ptr ', '').replace('byte ptr ', '')
                if tgt not in writes:
                    writes.append(tgt)
        if ins.mnemonic in ('inc', 'dec') and ops.startswith('dword ptr ['):
            t = ops.replace('dword ptr ', '')
            if t not in writes:
                writes.append('(r/w)' + t)
        if ins.mnemonic == 'call' and ops.startswith('0x'):
            t = int(ops, 16)
            if t not in calls:
                calls.append(t)
        if ins.mnemonic in ('cmp', 'test'):
            if ops not in conds:
                conds.append(ops)
    print('0x%08X  size=%-5d insn=%-4d' % (va, sz, len(insns)))
    print('   WRITES: %s' % (' | '.join(writes[:18]) if writes else '-'))
    print('   CALLS : %s' % (' '.join('0x%08X' % c for c in calls[:26]) if calls else '-'))
    print('   COND  : %s' % (' | '.join(conds[:10]) if conds else '-'))
    tail = insns[-4:]
    print('   TAIL  : %s' % ' ; '.join('%s %s' % (i.mnemonic, i.op_str) for i in tail))
    if full:
        for i in insns:
            print('      0x%08X  %-14s %s' % (i.address, i.mnemonic, i.op_str))
    print()


args = [a for a in sys.argv[1:] if not a.startswith('--')]
full = '--full' in sys.argv
for a in args:
    summarize(int(a, 16), full)

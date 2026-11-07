"""调用图闭包 + 覆盖面账本 (v2, 只扫可执行节, bisect 定位)

目的: 不再"手挑函数读", 而是从种子出发枚举整个可达调用图,
      给每个函数一行账: 地址 / 大小 / 调用边来源数 / 被调者数 / 是否在哪些层。

函数边界: 所有 E8/E9 目标 ∪ SEH 序言 ∪ 已知种子, 排序后 size = 到下一个入口。
已知盲区(v1 起就存在, 不假装覆盖):
  - 虚调用 `mov e,r,[b+d]; call r` 不产生边
  - 线性扫描会把指令中间的 0xE8/0xE9 误判为调用; 只保留落在可执行节内的目标以压制噪声

用法:
  python -I graph.py --depth 3 0xBBF940 0xBBE5C0
  python -I graph.py --depth 1 --mark 0xBBF940,0xBBE5C0,0xBBF2E0 0xBBF940
"""
import sys, bisect, struct, os
sys.path.insert(0, __file__.rsplit('\\', 1)[0])

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d = open(P, 'rb').read()

# ---------- 自己解析 PE 头, 拿到节属性 ----------
e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, e_lfanew + 6)[0]
opt_sz = struct.unpack_from('<H', d, e_lfanew + 20)[0]
ib = struct.unpack_from('<I', d, e_lfanew + 52)[0]
sec0 = e_lfanew + 24 + opt_sz
SECS = []
for k in range(nsec):
    o = sec0 + 40 * k
    name = d[o:o + 8].rstrip(b'\x00').decode('latin1')
    vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
    ch = struct.unpack_from('<I', d, o + 36)[0]
    SECS.append(dict(name=name, va=ib + va, vs=vs, ra=ra, rs=rs, ch=ch,
                     exec_=bool(ch & 0x20000000)))
EXEC = [s for s in SECS if s['exec_'] and s['ra'] and s['vs']]
print('节: %s' % ', '.join('%s%s' % (s['name'], '*' if s['exec_'] else '') for s in SECS))


def in_exec(va):
    return any(s['va'] <= va < s['va'] + max(s['vs'], s['rs']) for s in EXEC)


def read(va, n):
    for s in SECS:
        if s['va'] <= va < s['va'] + max(s['vs'], s['rs']):
            o = s['ra'] + (va - s['va'])
            if 0 <= o and o + n <= len(d):
                return d[o:o + n]
    return None


# ---------- 收集入口与调用边 ----------
# ★v3 修正: E9(jmp) 的目标绝大多数是**函数内部的跳转标号**, 不是函数入口。
#   把 E9 目标当入口会把大函数切成碎片(实测 0xBBF2E0 被切成 6 段)。
#   现在: 入口 = SEH 序言 ∪ E8(call) 目标。
#         边   = E8 一律算; E9 只有在目标本身已是入口(尾调用)时才算。
entries = set()
calls = []
jmp_edges = []
for s in EXEC:
    blob = d[s['ra']:s['ra'] + min(max(s['vs'], s['rs']), len(d) - s['ra'])]
    base = s['va']
    for op, is_call in ((b'\xe8', True), (b'\xe9', False)):
        i = blob.find(op)
        while i >= 0:
            if i + 5 <= len(blob):
                rel = struct.unpack_from('<i', blob, i + 1)[0]
                tgt = (base + i + 5 + rel) & 0xFFFFFFFF
                if in_exec(tgt):
                    if is_call:
                        entries.add(tgt)
                        calls.append((base + i, tgt))
                    else:
                        jmp_edges.append((base + i, tgt))
            i = blob.find(op, i + 1)
    SEH = b'\x55\x8b\xec\x6a\xff\x68'
    i = blob.find(SEH)
    while i >= 0:
        entries.add(base + i)
        i = blob.find(SEH, i + 1)

# 尾调用: 只保留指向真实入口的 jmp
calls.extend((va, t) for va, t in jmp_edges if t in entries)

calls.sort()
CALL_VAS = [c[0] for c in calls]
entries = sorted(entries)
ENT = entries


def size_of(va):
    k = bisect.bisect_right(ENT, va)
    return (ENT[k] - va) if k < len(ENT) else 0


def callees_of(va):
    sz = size_of(va)
    if sz <= 0:
        return []
    a = bisect.bisect_left(CALL_VAS, va)
    b = bisect.bisect_left(CALL_VAS, va + sz)
    return [calls[j][1] for j in range(a, b)]


backref = {}
for va, t in calls:
    backref.setdefault(t, []).append(va)

# ---------- 参数 ----------
args = sys.argv[1:]
depth, marks, seeds = 2, set(), []
i = 0
while i < len(args):
    if args[i] == '--depth':
        depth = int(args[i + 1], 0); i += 2
    elif args[i] == '--mark':
        marks = set(int(x, 16) for x in args[i + 1].split(',')); i += 2
    elif args[i] == '--summary':
        i += 1
    else:
        seeds.append(int(args[i], 16)); i += 1

# ---------- BFS ----------
seen, order = {}, []
front = [(s, 0) for s in seeds]
for s, _ in front:
    seen[s] = 0
while front:
    nxt = []
    for f, dep in front:
        order.append((f, dep))
        if dep >= depth:
            continue
        for t in callees_of(f):
            if t not in seen:
                seen[t] = dep + 1
                nxt.append((t, dep + 1))
    front = nxt

LAYER = ((0xBB0000, 0xBE0000, 'DTLS'), (0x7E0000, 0x800000, 'dwRoom'),
         (0xC70000, 0xC80000, 'crypto'), (0xBB0000, 0xBC0000, 'DTLS-core'))
order.sort()
total = sum(size_of(f) for f, _ in order)
read_n = sum(1 for f, _ in order if f in marks)
read_b = sum(size_of(f) for f, _ in order if f in marks)
print('\n可执行节内入口 %d 个; 本次闭包 %d 个函数, 函数体合计 %d 字节 (%.1f KB)\n'
      % (len(ENT), len(order), total, total / 1024.0))
print('其中已读 %d 个 / %d 字节 (%.1f%% 的函数数, %.1f%% 的字节数)\n'
      % (read_n, read_b, 100.0 * read_n / max(1, len(order)), 100.0 * read_b / max(1, total)))

if '--summary' in args:
    print('--- 未读函数(闭包内) ---')
    for f, dep in order:
        if f in marks:
            continue
        lay = ''
        for lo, hi, nm in LAYER:
            if lo <= f < hi:
                lay = nm; break
        print('  0x%08X  size=%-5d call#=%-4d cal#=%-3d dep=%d %s'
              % (f, size_of(f), len(backref.get(f, [])), len(callees_of(f)), dep, lay))
    print('\n★ 盲区: 虚调用不产生边; 本闭包只覆盖直接调用可达的部分。')
    sys.exit(0)


print('%-10s %-6s %-4s %-4s %-4s %s' % ('entry', 'size', 'call#', 'cal#', 'dep', 'layer / 已读'))
stat = {}
for f, dep in order:
    sz = size_of(f)
    cal = len(callees_of(f))
    nin = len(backref.get(f, []))
    lay = ''
    for lo, hi, nm in LAYER:
        if lo <= f < hi:
            lay = nm; break
    mk = '  ★已读' if f in marks else ''
    print('0x%08X %-6d %-4d %-4d %-4d %s%s' % (f, sz, nin, cal, dep, lay, mk))
print('\n★ 盲区: 虚调用不产生边; 本闭包只覆盖直接调用可达的部分。')

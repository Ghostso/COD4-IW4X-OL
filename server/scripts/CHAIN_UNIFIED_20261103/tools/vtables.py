"""枚举 PE 里所有 vtable（MSVC RTTI 布局），补"虚分派盲区"。

判定: 一段 4 字节对齐的连续 dword，全部指向可执行节 ⇒ 疑似 vtable。
      若这段之前(或之后)紧邻一个指向非可执行节的 dword ⇒ 那是 COL(RTTI Complete Object Locator)，
      说明确实是 vtable 而非普通函数表。

用法:
  python -I vtables.py                 # 统计 + 前 N 个
  python -I vtables.py --addr 0xD5AFA4 # 逐槽展开某个 vtable
  python -I vtables.py --slots 0xBB0000,0xBC3000   # 只输出槽目标落在给定区间的
"""
import sys, struct
sys.path.insert(0, __file__.rsplit('\\', 1)[0])

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
    nm = d[p:p + 8].rstrip(b'\x00').decode('latin1')
    vs, va, rs, ra = struct.unpack_from('<IIII', d, p + 8)
    ch = struct.unpack_from('<I', d, p + 36)[0]
    SECS.append(dict(name=nm, va=ib + va, vs=vs, ra=ra, rs=rs, exec_=bool(ch & 0x20000000)))


def sec_of(va):
    for s in SECS:
        if s['va'] <= va < s['va'] + max(s['vs'], s['rs']):
            return s
    return None


def in_exec(va):
    s = sec_of(va)
    return bool(s and s['exec_'])


def rd(va):
    s = sec_of(va)
    if not s:
        return None
    o = s['ra'] + (va - s['va'])
    if 0 <= o and o + 4 <= len(d):
        return struct.unpack_from('<I', d, o)[0]
    return None


args = sys.argv[1:]

if '--addr' in args:
    a = int(args[args.index('--addr') + 1], 16)
    print('vtable 0x%08X:' % a)
    # COL 在 vtable 前一个 dword
    col = rd(a - 4)
    print('   COL(前一个 dword) = 0x%08X' % (col if col is not None else 0))
    i = 0
    while True:
        v = rd(a + 4 * i)
        if v is None or not in_exec(v):
            print('   [+0x%02X] = 0x%08X  ← 非代码, 表尾' % (4 * i, v if v is not None else 0))
            break
        print('   [+0x%02X] = 0x%08X' % (4 * i, v))
        i += 1
        if i > 64:
            break
    sys.exit(0)

only = None
if '--slots' in args:
    lo, hi = args[args.index('--slots') + 1].split(',')
    only = (int(lo, 16), int(hi, 16))

# ---- 全镜像扫 vtable ----
found = []
for s in SECS:
    if s['exec_']:
        continue
    size = min(s['vs'], s['rs'])
    if size <= 0:
        continue
    lo = s['va']
    blob = d[s['ra']:s['ra'] + size]
    i = 0
    while i + 8 <= len(blob):
        v = struct.unpack_from('<I', blob, i)[0]
        if not in_exec(v):
            i += 4
            continue
        # 向下扩张连续可执行指针
        j = i
        cnt = 0
        while j + 4 <= len(blob):
            w = struct.unpack_from('<I', blob, j)[0]
            if not in_exec(w):
                break
            cnt += 1
            j += 4
        if cnt >= 2:
            prev = struct.unpack_from('<I', blob, i - 4)[0] if i >= 4 else 0
            prev_ok = bool(prev) and not in_exec(prev)
            if prev_ok:
                slots = [struct.unpack_from('<I', blob, i + 4 * k)[0] for k in range(cnt)]
                found.append((lo + i, slots))
            i = j
        else:
            i += 4

print('发现 vtable %d 个 (带 COL 前缀、>=2 槽)' % len(found))
tot = sum(len(s) for _, s in found)
print('槽总数 %d' % tot)

if only:
    lo, hi = only
    hits = [(a, s) for a, s in found if any(lo <= v < hi for v in s)]
    print('\n槽目标落在 [0x%08X,0x%08X) 的 vtable: %d 个' % (lo, hi, len(hits)))
    for a, s in hits:
        print('  0x%08X (%d 槽): %s' % (a, len(s),
              ' '.join('0x%08X' % v for v in s[:12])))
else:
    from collections import Counter
    c = Counter(len(s) for _, s in found)
    print('\n按槽数分布: %s' % dict(sorted(c.items())))
    print('\n前 40 个:')
    for a, s in found[:40]:
        print('  0x%08X (%2d 槽)' % (a, len(s)))

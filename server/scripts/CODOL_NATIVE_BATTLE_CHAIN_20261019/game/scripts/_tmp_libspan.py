"""临时（只读）：用「源码文件名」指纹求每个第三方库在 .text 里的精确区段。

第三方静态库会把自己源码文件路径串写进 .rdata，并由本库代码引用。
按引用指令地址排序后，每个库会形成连续区间；区间之间的空隙 = 非库代码。

用法: python scripts/_tmp_libspan.py
输出: scripts/_out/libspan.txt
"""
import sys, os, re, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000
RD_HI = IMAGE_BASE + 0x009af000
RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')

# 源码路径/库指纹 -> 库名
LIB = [
    (re.compile(r'\\sources\\modules\\'), 'OpenCV'),
    (re.compile(r'\bcv[A-Z]\w+'), 'OpenCV'),
    (re.compile(r'^(\.\\)?ssl\\'), 'OpenSSL'),
    (re.compile(r'^(\.\\)?crypto\\'), 'OpenSSL'),
    (re.compile(r'^(\.\\)?engines\\'), 'OpenSSL'),
    (re.compile(r'^(\.\\)?apps\\'), 'OpenSSL'),
    (re.compile(r'\bSQLite format 3\b'), 'SQLite'),
    (re.compile(r'^sqlite_'), 'SQLite'),
    (re.compile(r'\bTIFF'), 'libtiff'),
    (re.compile(r'\bpng_'), 'libpng'),
    (re.compile(r'\bdeflate\b|\binflate\b|\badler32\b'), 'zlib'),
    (re.compile(r'^libcurl/'), 'libcurl'),
    (re.compile(r'\bCURLOPT_|\bCURLINFO_'), 'libcurl'),
    (re.compile(r'^lua[A-Z_]|^attempt to |^stack overflow$|^bad argument'), 'Lua'),
    (re.compile(r'\.lua\b'), 'Lua'),
    (re.compile(r'^invalid (map/set|bitset)|^list<T> too long'), 'MSVC-STL'),
]

# 关注的函数（用户第一任务清单）
TARGETS = [
    0x10425370, 0x10425530, 0x1042d930, 0x1042c910, 0x1042cc70, 0x10431460,
    0x1044b240, 0x1044d060, 0x1044cfc0,
    0x10650900, 0x10650ac0, 0x10650cfe, 0x10670d50, 0x1066fea0, 0x10670120,
    0x106747c0, 0x1065fca0,
]


def libof(s):
    if not s:
        return None
    for rx, name in LIB:
        if rx.search(s):
            return name
    return None


def main():
    img = Image()
    sec = [x for x in img.sections if x['name'] == '.text'][0]
    buf = img.data[sec['raw']:sec['raw'] + sec['rawsize']]
    base = sec['va']
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    hits = []          # (ins_va, libname, str)
    i = 0
    n = len(buf)
    while i < n:
        got = 0
        for (addr, size, mn, ops) in md.disasm_lite(buf[i:], IMAGE_BASE + base + i):
            got = (addr - (IMAGE_BASE + base + i)) + size
            for m in RE_IMM.finditer(ops):
                v = int(m.group(1), 16)
                if RD_LO <= v < RD_HI:
                    try:
                        s = img.cstr(v - IMAGE_BASE, 80)
                    except Exception:
                        s = None
                    L = libof(s)
                    if L:
                        hits.append((addr, L, s))
        if got == 0:
            i += 1
        else:
            i += got

    hits.sort()
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'libspan.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    P('=== 1. 库指纹引用，按指令地址排序 (%d 条) ===' % len(hits))
    P('（同库连续行=该库代码区段；库名跳变处=区段边界）')
    prev = None
    for (a, L, s) in hits:
        if L != prev:
            P('---- [%s] 起于 0x%08x ----' % (L, a))
            prev = L
        P('   0x%08x  %-9s %r' % (a, L, s[:70]))
    P()

    # 每个库的 .text 覆盖区间
    P('=== 2. 每库 .text 区段（合并 32KB 内相邻）===')
    bylib = collections.defaultdict(list)
    for (a, L, s) in hits:
        bylib[L].append(a)
    spans = []
    for L, lst in bylib.items():
        lst = sorted(set(lst))
        runs = []
        st = lst[0]
        pv = lst[0]
        for a in lst[1:]:
            if a - pv > 0x8000:
                runs.append((st, pv))
                st = a
            pv = a
        runs.append((st, pv))
        for (s0, s1) in runs:
            spans.append((s0, s1, L))
        P('%-9s  %d 条引用 / %d 段: %s' % (L, len(lst), len(runs),
           ', '.join('0x%08x-0x%08x' % (x, y) for (x, y) in runs)))
    P()

    P('=== 3. 合并后的 .text 库区段总表（按起始排序）===')
    spans.sort()
    for (s0, s1, L) in spans:
        P('   0x%08x - 0x%08x  (0x%06x)  %s' % (s0, s1, s1 - s0, L))
    P()

    P('=== 4. 空隙（未被任何库指纹覆盖的 .text 区间）===')
    merged = []
    for (s0, s1, L) in sorted(spans):
        if merged and s0 <= merged[-1][1] + 0x8000:
            merged[-1][1] = max(merged[-1][1], s1)
        else:
            merged.append([s0, s1])
    TEXT_LO = IMAGE_BASE + sec['va']
    TEXT_HI = IMAGE_BASE + sec['va'] + sec['rawsize']
    cur = TEXT_LO
    for (s0, s1) in merged:
        if s0 - cur > 0x8000:
            P('   0x%08x - 0x%08x  (0x%06x)  非库代码' % (cur, s0, s0 - cur))
        cur = max(cur, s1)
    if TEXT_HI - cur > 0x8000:
        P('   0x%08x - 0x%08x  (0x%06x)  非库代码' % (cur, TEXT_HI, TEXT_HI - cur))
    P()

    P('=== 5. 用户第一任务清单函数落在哪个库区段 ===')
    for t in TARGETS:
        owner = None
        for (s0, s1, L) in sorted(spans):
            if s0 - 0x2000 <= t <= s1 + 0x2000:
                owner = (L, s0, s1)
                break
        near = [h for h in hits if abs(h[0] - t) < 0x4000]
        nearstr = '; '.join('%s@0x%08x' % (L, a) for (a, L, s) in near[:4])
        if owner:
            P('  0x%08x  -> %-9s (区段 0x%08x-0x%08x)  近邻: %s'
              % (t, owner[0], owner[1], owner[2], nearstr))
        else:
            P('  0x%08x  -> [非库代码]  近邻: %s' % (t, nearstr))
    out.close()
    print('-> scripts/_out/libspan.txt  (%d 条库指纹引用)' % len(hits))


if __name__ == '__main__':
    main()

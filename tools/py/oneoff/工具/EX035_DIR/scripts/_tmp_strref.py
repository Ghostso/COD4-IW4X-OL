# -*- coding: utf-8 -*-
import sys, os, re, struct, bisect, collections
sys.path.insert(0, os.path.abspath('scripts'))
from pe import Image
import x86callers as X
img = Image()
IB = 0x10000000
sec = [s for s in img.sections if s['name'] == '.text'][0]
base = IB + sec['va']
buf = img.read(sec['va'], sec['rawsize'])
RD_LO, RD_HI = IB + 0x743000, IB + 0x9af000

def s_at(va):
    try:
        s = img.cstr(va - IB, 120)
    except Exception:
        return None
    if not s:
        return None
    good = sum(1 for c in s if 32 <= ord(c) < 127)
    if good < len(s) * 0.9 or len(s) < 4:
        return None
    return s

def scan(lo, hi, tag):
    hits = collections.OrderedDict()
    for i in range(len(buf) - 4):
        v = struct.unpack_from('<I', buf, i)[0]
        if not (RD_LO <= v < RD_HI):
            continue
        va = base + i
        if not (lo <= va < hi):
            continue
        s = s_at(v)
        if s:
            hits.setdefault(s, []).append(va)
    print('')
    print('=== %s : 引用 .rdata 字符串 %d 条 ===' % (tag, len(hits)))
    for s, sites in hits.items():
        print('  %-62s  x%d  e.g. 0x%08x' % (repr(s)[1:-1][:62], len(sites), sites[0]))

print('func_start lookup ...')
dct = X.direct_call_targets(img)
starts = X.func_starts(img, dct)
def owner(va):
    i = bisect.bisect_right(starts, va) - 1
    return starts[i] if i >= 0 else None

scan(IB + 0x420000, IB + 0x450000, 'A 窗口 0x00420000-0x00450000')
scan(IB + 0x640000, IB + 0x690000, 'B 窗口 0x00640000-0x00690000')

def callers_of(target_va, limit=20):
    res = []
    for i in range(len(buf) - 5):
        if buf[i] != 0xE8:
            continue
        rel = struct.unpack_from('<i', buf, i + 1)[0]
        src = base + i
        if (src + 5 + rel) & 0xffffffff == target_va:
            res.append(src)
    return res[:limit]

for va, tag in ((IB + 0x44b240, 'A getaddrinfo wrapper'),
                (IB + 0x65fca0, 'B getaddrinfo wrapper'),
                (IB + 0x431460, 'A bind+listen host'),
                (IB + 0x6747c0, 'B bind+listen host'),
                (IB + 0x4259a0, 'A Curl_connect-ish')):
    cs = callers_of(va)
    print('')
    print('== 调用 %s 0x%08x : %d ==' % (tag, va, len(cs)))
    for c in cs:
        print('   call @0x%08x  owner 0x%08x' % (c, owner(c) or 0))

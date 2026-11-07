# -*- coding: utf-8 -*-
import sys, os, re, struct, bisect
sys.path.insert(0, os.path.abspath('scripts'))
from pe import Image
import x86callers as X
img = Image()
IB = 0x10000000
sec = [s for s in img.sections if s['name'] == '.text'][0]
base = IB + sec['va']
buf = img.read(sec['va'], sec['rawsize'])

dct = X.direct_call_targets(img)
starts = X.func_starts(img, dct)
print('func_starts: %d 个, direct_call_targets: %d' % (len(starts), len(dct)))

def owner(va):
    i = bisect.bisect_right(starts, va) - 1
    return starts[i] if i >= 0 else None

def callers_of(target_va):
    res = []
    for i in range(len(buf) - 5):
        if buf[i] != 0xE8:
            continue
        rel = struct.unpack_from('<i', buf, i + 1)[0]
        src = base + i
        if (src + 5 + rel) & 0xffffffff == target_va:
            res.append(src)
    return res

def immrefs(val):
    needle = struct.pack('<I', val)
    res = []
    p = buf.find(needle)
    while p != -1:
        res.append(base + p)
        p = buf.find(needle, p + 1)
    return res

TARGETS = [
    (IB + 0x425530, 'A connect 0x00425530'),
    (IB + 0x425370, 'A socket wrapper 0x00425370'),
    (IB + 0x44d060, 'A inet_ntop-ish 0x0044d060'),
    (IB + 0x650900, 'B socket 0x00650900'),
    (IB + 0x650a10, 'B cand-entry 0x00650a10'),
    (IB + 0x650a60, 'B cand-entry 0x00650a60'),
    (IB + 0x650ac0, 'B cand-entry 0x00650ac0'),
    (IB + 0x650cfe, 'B FAKE entry 0x00650cfe'),
]
for va, tag in TARGETS:
    cs = callers_of(va)
    print('')
    print('== %s (VA 0x%08x)  直接调用点 %d ==' % (tag, va, len(cs)))
    for c in cs[:30]:
        print('   call @ 0x%08x   owner 0x%08x' % (c, owner(c) or 0))

print('')
for val, tag in ((0x107acd00, 'Immediate connect fail'), (0x107acd54, 'Trying %s:%ld'),
                 (0x107acd24, 'sa_addr inet_ntop failed'), (0x107ab797, 'libcurl/7.65.1')):
    rs = immrefs(val)
    print('== imm32 0x%08x (%s) 引用 %d ==' % (val, tag, len(rs)))
    for r in rs[:20]:
        print('   @0x%08x owner 0x%08x' % (r, owner(r) or 0))

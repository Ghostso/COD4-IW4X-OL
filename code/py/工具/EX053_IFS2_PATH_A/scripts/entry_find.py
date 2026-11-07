import sys, os, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
img = Image()

dct = X.direct_call_targets(img)
starts = X.func_starts(img, dct)
sset = set(starts)

def near(va, back=0x900):
    lo = va - back
    i = bisect.bisect_left(starts, lo)
    out = []
    while i < len(starts) and starts[i] < va:
        out.append(starts[i]); i += 1
    return out

def raw(va, n=16):
    return img.data[img.va2raw(va):img.va2raw(va)+n].hex() if hasattr(img,'va2raw') else ''

for tag, va in [('A connect call', 0x00425802), ('B connect call', 0x00650d4e),
                ('A bind+listen', 0x00431460), ('B bind+listen', 0x006747c0)]:
    print('== %s @ 0x%08x' % (tag, va))
    ns = near(va)
    print('   前 8 个候选入口:', ' '.join('0x%08x' % x for x in ns[-8:]))
    for x in ns[-4:]:
        print('     0x%08x  %s' % (x, repr(img.cstr(x-8, 40)) if False else ''))
    print()

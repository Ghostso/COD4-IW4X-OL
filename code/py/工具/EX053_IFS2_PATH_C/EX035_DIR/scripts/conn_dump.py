import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
img = Image()
def dump(lo, hi, tag, only=None):
    print('='*78); print('### %s [0x%08x,0x%08x]' % (tag, lo, hi)); print('='*78)
    for ins in X.dis(img, lo, hi-lo):
        op = ins.op_str; mn = ins.mnemonic
        if only == 'stack':
            interesting = ('[esp + 0x' in op or '[ebp' in op or mn in ('call','ret') or
                           'edi' in op or 'ebp,' in op or 'ebp,' in op)
            if not interesting: continue
        print('  %08x  %-18s %-12s %s' % (ins.address, ins.bytes.hex(), mn, op))
dump(0x00425530, 0x00425600, 'A connect 函数 头部')
dump(0x00425600, 0x004256a0, 'A 中段1')
dump(0x004256a0, 0x00425700, 'A 中段2')

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
img = Image()

def show(lo, hi, tag):
    print('='*78); print('### %s  [0x%08x, 0x%08x]' % (tag, lo, hi)); print('='*78)
    for ins in X.dis(img, lo, hi-lo):
        print('  %08x  %-20s %-14s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

show(0x00425770, 0x00425830, 'A connect 附近')
show(0x00650ce0, 0x00650d80, 'B connect 附近')

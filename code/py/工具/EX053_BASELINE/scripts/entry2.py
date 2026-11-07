import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
img = Image()
def rawhex(va, n):
    r = img.va2raw(va)
    return img.data[r:r+n]
def dump(lo, hi, tag):
    print('='*74); print('### %s [0x%08x,0x%08x]' % (tag, lo, hi)); print('='*74)
    for ins in X.dis(img, lo, hi-lo):
        print('  %08x  %-18s %-12s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
print('A 区 0x00425740 前 64 字节原始:'); print(' ', rawhex(0x00425740,64).hex(' '))
print('B 区 0x00650c90 前 112 字节原始:'); print(' ', rawhex(0x00650c90,112).hex(' '))
print()
# 从可疑边界重解
dump(0x00425760, 0x004257a0, 'A 边界区重解')
dump(0x00650cb0, 0x00650d00, 'B 边界区重解')

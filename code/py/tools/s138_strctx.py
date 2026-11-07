import re
import sys
d = open(r'E:\codol_re\client_image_20261027.bin', 'rb').read()
VA = 0x400000


def ctx(off, back=40, fwd=120):
    a = max(0, off - back)
    b = min(len(d), off + fwd)
    s = d[a:b]
    return ''.join(chr(c) if 32 <= c < 127 else '.' for c in s)


for a in sys.argv[1:]:
    off = int(a, 0) - VA
    print('== 0x%08X ==' % int(a, 0))
    print(ctx(off))
    print()

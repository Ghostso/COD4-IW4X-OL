# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.abspath('scripts'))
from pe import Image
img = Image()
print('--- sections: name va vsize raw rawsize ---')
for s in img.sections:
    print('   %-10s va=0x%08x vsize=0x%-8x raw=0x%08x rawsize=0x%x' %
          (s['name'], s['va'], s['vsize'], s['raw'], s['rawsize']))
print()
def off_of_rva(rva):
    for s in img.sections:
        if s['va'] <= rva < s['va'] + max(s['vsize'], s['rawsize']):
            return s['raw'] + (rva - s['va'])
    return None
for rva in (0x7acd54, 0x7acd00, 0x7acd24, 0x7acd30, 0x7acd40, 0x7acd68, 0x7ab797):
    o = off_of_rva(rva)
    raw = img.data[o:o+120] if o is not None else b'?'
    txt = re.split(rb'\x00', raw)[0].decode('latin-1')
    print('RVA 0x%08x -> file 0x%08x  ""%s""' % (rva, o, txt[:100]))
print()
print('--- cstr(RVA) 交叉验证 ---')
for rva in (0x7acd54, 0x7acd00, 0x7ab797):
    try:
        print('   cstr(0x%08x) = %r' % (rva, img.cstr(rva, 100)))
    except Exception as e:
        print('   cstr(0x%08x) 失败 %r' % (rva, e))

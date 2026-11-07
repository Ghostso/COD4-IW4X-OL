import os
ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
d = open(os.path.join(ROOT, 'LocalRM.dll'), 'rb').read()
o = open(os.path.join(ROOT, r'工具\EX035_DIR\IIPS\iips.dll'), 'rb').read()

print('=== .data raw 0x42000..0x42420 (gen) ===')
for k in range(0x42000, 0x42420, 16):
    m = ''.join('X' if d[j] != o[j] else '.' for j in range(k, k+16))
    print('%06x %s  o %s' % (k, m, o[k:k+16].hex()))
    print('              g %s' % d[k:k+16].hex())

print()
print('=== .rdata raw 0x33000..0x33090 (gen, overwritten area) ===')
for k in range(0x33000, 0x33090, 16):
    m = ''.join('X' if d[j] != o[j] else '.' for j in range(k, k+16))
    print('%06x %s  o %s' % (k, m, o[k:k+16].hex()))
    print('              g %s' % d[k:k+16].hex())

print()
print('=== does LocalRM.dll still match ANY pristine iips.dll? ===')
import hashlib
for p, l in ((os.path.join(ROOT, r'工具\EX035_DIR\IIPS\iips.dll'), 'EX035_DIR'),
             (os.path.join(ROOT, r'COD OL\IIPS\iips.dll'), 'COD OL/IIPS'),
             (os.path.join(ROOT, r'工具\EB1_SANDBOX\IIPS\iips.dll'), 'EB1_SANDBOX')):
    od = open(p, 'rb').read()
    n = sum(1 for k in range(len(d)) if k < len(od) and d[k] != od[k])
    print(f'  vs {l:14s} size={len(od):#x} differing_bytes={n}')

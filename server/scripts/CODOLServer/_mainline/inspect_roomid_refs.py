"""逐个检查含 roomId 的 4 个地址，判断哪个是房间对象 / 路由表项。

地址（snap_003/004 一致）:
  0x08425C10
  0x08426368
  0x0E374660   <- 路由表项 (表 0xE376C08 - 0x25A8)
  0x3AC62E5D   <- 奇数地址，可能是误命中

对每个：
  - 前后 64 字节
  - 若首 dword 像 vtable，解 RTTI 类名
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
TARGETS = [0x08425C10, 0x08426368, 0x0E374660, 0x3AC62E5D]

snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
cover = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')


def covered(va, n):
    off = va - lo
    if off < 0:
        return False
    cover.seek(off)
    return cover.read(n) == b'\x01' * n


def read(va, n):
    if not covered(va, n):
        return None
    f.seek(va - lo)
    d = f.read(n)
    return d if len(d) == n else None


def cstr(va, maxn=128):
    b = read(va, maxn)
    if not b:
        return None
    e = b.find(b'\x00')
    return b[:e if e >= 0 else maxn].decode('latin1', 'replace')


def rtti(vt):
    p = read(vt - 4, 4)
    if not p:
        return '(vtable-4 不可读)'
    col = struct.unpack('<I', p)[0]
    if col == 0:
        return '(无 RTTI)'
    hdr = read(col, 0x10)
    if not hdr:
        return '(COL 0x%08X 不可读)' % col
    sig, off, cd, td = struct.unpack('<IIII', hdr)
    if not td:
        return '(td=0)'
    name = cstr(td + 8, 200)
    return name or '(名字不可读 @0x%08X)' % (td + 8)


for va in TARGETS:
    print('=== 0x%08X ===' % va)
    base = va & ~3
    d = read(base - 0x10, 0x60)
    if not d:
        print('  不可读')
        print()
        continue
    for i in range(0, len(d), 16):
        chunk = d[i:i + 16]
        vals = ' '.join('%08X' % struct.unpack_from('<I', chunk, k)[0]
                        for k in range(0, len(chunk) - 3, 4))
        mark = '  <<<' if base - 0x10 + i <= va < base - 0x10 + i + 16 else ''
        print('  %+04X  %s%s' % (i - 0x10, vals, mark))
    first = struct.unpack_from('<I', d, 0x10)[0]
    if 0x00400000 <= first < 0x01000000 or 0x00C00000 <= first < 0x01000000:
        print('  首 dword 0x%08X 像 vtable -> %s' % (first, rtti(first)))
    print()

print('=== 路由表项 0x0E376C08 完整内容 ===')
d = read(0x0E376C08 - 0x25B8, 0x40)
if d:
    for i in range(0, len(d), 16):
        vals = ' '.join('%08X' % struct.unpack_from('<I', d, i + k)[0]
                        for k in range(0, 16, 4))
        print('  entry+%03X  %s' % (i, vals))
    w = struct.unpack_from('<16I', d, 0)
    print()
    print('  flag1(+0x00)=%d  flag2(+0x01)=%d' % (w[0] & 0xFF, (w[0] >> 8) & 0xFF))
    print('  +0x10 = 0x%08X   +0x14 = 0x%08X' % (w[4], w[5]))
    h = read(0x0E376C08, 4)
    if h:
        print('  handler = 0x%08X' % struct.unpack('<I', h)[0])
else:
    print('  不可读')

cover.close()
f.close()

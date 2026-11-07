"""确认房间对象 vtable 0x7E9FCCB8 的类名, 并给出完整对象结构。

已确定:
    基址 0x08425C08
      +000  vtable = 0x7E9CCB8  (待解 RTTI)
      +004  0
      +008  roomId_lo      <- 0x7E79C0 校验的 [obj+8]
      +00C  roomId_hi      <- 0x7E79C0 校验的 [obj+0xc]
      +010  0
      +014  0x00000101     (flag 字节对)
      ...
该对象被 11 处引用, 是真实使用的对象。
"""
import json
import os
import struct
import sys

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
meta = json.load(open(os.path.join(RUN, 'snap_003.json'), encoding='utf-8'))
lo = meta['lo']
cov = open(os.path.join(RUN, 'snap_003_cover.bin'), 'r+b')
f = open(os.path.join(RUN, 'snap_003.bin'), 'rb')


def read(va, n):
    off = va - lo
    if off < 0:
        return None
    cov.seek(off)
    if cov.read(n) != b'\x01' * n:
        return None
    f.seek(off)
    d = f.read(n)
    return d if len(d) == n else None


def cstr(va, maxn=200):
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
    if col == 0 or col < 0x400000:
        return '(COL=0x%08X, 非 RTTI)' % col
    hdr = read(col, 0x10)
    if not hdr:
        return '(COL 0x%08X 不可读)' % col
    sig, off, cd, td = struct.unpack('<IIII', hdr)
    if not td:
        return '(td=0)'
    name = cstr(td + 8)
    return (name or '(不可读)') + '  [COL=0x%08X td=0x%08X]' % (col, td)


OBJ = 0x08425C08
print('=== 房间对象 0x%08X ===' % OBJ)
d = read(OBJ, 0x60)
if d:
    for i in range(0, len(d), 16):
        w = struct.unpack_from('<4I', d, i)
        vals = ' '.join('%08X' % x for x in w)
        note = ''
        if i == 0:
            note = '  <- vtable'
        elif i == 8:
            note = '  <- roomId lo / hi  (0x7E79C0 校验的 obj+8/+0xC)'
        print('  +%03X  %s%s' % (i, vals, note))

print()
vt = struct.unpack_from('<I', d, 0)[0] if d else 0
print('vtable = 0x%08X' % vt)
print('类名   = %s' % rtti(vt))

print()
print('=== 该对象的 vtable 前若干槽 ===')
if vt:
    vd = read(vt, 0x40)
    if vd:
        for i in range(0, 0x40, 4):
            v = struct.unpack_from('<I', vd, i)[0]
            print('  slot[%2d] = 0x%08X' % (i // 4, v))

cov.close()
f.close()

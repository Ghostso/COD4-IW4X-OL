"""在 snap_003 里看 0xE76C00 那块附近，有没有 handler 指针 / 注册表结构。

AS_* 名字在 0xE76A00~0xE76E00 一带。
若这是"名字表 + 并行 handler 数组"，handler 应在其附近。
若附近全是其他类名（相互紧挨），那就是纯 RTTI 字符串区，没有注册表。

同时看这块的**起始和结束**，判断它到底是 RTTI 字符串段还是别的。
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')


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


def show(va, n, label):
    d = read(va, n)
    print('--- %s 0x%08X (%d B) ---' % (label, va, n))
    if not d:
        print('  不可读')
        return
    cur, cs = bytearray(), None
    for i, c in enumerate(d):
        if 32 <= c < 127:
            if cs is None:
                cs = i
            cur.append(c)
        else:
            if len(cur) >= 4:
                print('   0x%08X  %s' % (va + cs, cur.decode()))
            cur, cs = bytearray(), None
    if len(cur) >= 4:
        print('   0x%08X  %s' % (va + cs, cur.decode()))


# 名字块前后各看 0x400，看边界
show(0x00E76000, 0x1000, 'AS_* 名字块前后')

cov.close()
f.close()

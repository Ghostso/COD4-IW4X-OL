"""解出包含 0x7F1060 的 vtable(0xDE07A0 起) 所属的类名。

RTTI 规则(项目已实测): vtable[-1] = CompleteObjectLocator(COL)
    COL+0x0C = TypeDescriptor 指针
    TD+0x08  = 名字串 (".?AVxxx@@")
"""
import os
import struct

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))
CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


def cstr(va, maxn=160):
    b = read_at(va, maxn)
    if not b:
        return None
    end = b.find(b'\x00')
    return b[:end if end >= 0 else maxn].decode('latin1', 'replace')


def resolve(vtable_va, label=''):
    colp = read_at(vtable_va - 4, 4)
    if not colp:
        print('%s vtable 0x%08X: 不可读' % (label, vtable_va))
        return
    col = struct.unpack('<I', colp)[0]
    if not col:
        print('%s vtable 0x%08X: COL=0 (无 RTTI)' % (label, vtable_va))
        return
    hdr = read_at(col, 0x10)
    if not hdr:
        print('%s vtable 0x%08X: COL 0x%08X 不可读' % (label, vtable_va, col))
        return
    sig, off, cd, td = struct.unpack('<IIII', hdr)
    name = cstr(td + 8) if td else None
    print('%s vtable 0x%08X  COL=0x%08X sig=%d off=%d td=0x%08X'
          % (label, vtable_va, col, sig, off, td))
    print('      类名: %s' % (name if name else '(无法解出)'))


# 已知的锚点: 0xDE07BC 存 0x7F1060。
# 表可能不从 0xDE07A0 开始; 先试几个可能的 vtable 起点。
for va in (0x00DE07A0, 0x00DE07A4, 0x00DE07A8, 0x00DE0790, 0x00DE0780):
    resolve(va)

print()
print('--- 用项目已有的 dwroom vtable 清单做对照(应能解出类名) ---')
resolve(0x00DC751C, '[对照] StartGame')
resolve(0x00DC7274, '[对照] dwRoomImp')

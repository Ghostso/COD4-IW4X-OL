"""直接从内存转储里定位所有 dwRoomMessage* TypeDescriptor 及其 vtable。

先扫描全部内存找到每个 "?AVdwRoomMessage..." 字符串的真实地址,
再从该地址向前找 '.?AV' 前缀确定 TypeDescriptor 起点,
然后按 MSVC 32 位 RTTI 链找 COL -> vtable。
"""
import os
import struct
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4])

IMG_BASE = 0x400000
CACHE = {}


def blob(base):
    if base not in CACHE:
        CACHE[base] = open(os.path.join(D, regions[base][1]), 'rb').read()
    return CACHE[base]


def read_at(va, n):
    for base, (size, fn) in regions.items():
        if base <= va < base + size and va + n <= base + size:
            return blob(base)[va - base:va - base + n]
    return None


def u32_at(va):
    r = read_at(va, 4)
    return struct.unpack('<I', r)[0] if r else None


def find_u32(val, limit=300):
    pat = struct.pack('<I', val)
    out = []
    for base, (size, fn) in sorted(regions.items()):
        d = blob(base)
        pos = 0
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            out.append(base + i)
            pos = i + 1
            if len(out) >= limit:
                return out
    return out


# 1. 找所有 "?AVdwRoomMessage" 的精确位置
targets = {}
for base, (size, fn) in sorted(regions.items()):
    d = blob(base)
    pos = 0
    while True:
        i = d.find(b'?AVdwRoomMessage', pos)
        if i < 0:
            break
        end = d.find(b'\x00', i)
        if end > i and end - i < 120:
            nm = d[i:end].decode('latin1')
            targets[nm] = base + i
        pos = i + 1

print('找到 %d 个 dwRoomMessage 类型名' % len(targets))
for nm, va in sorted(targets.items())[:15]:
    print('  0x%08X  %s' % (va, nm))
print()

# 2. 关键几个: 找 vtable
print('=== 解析 vtable ===')
for nm, name_va in sorted(targets.items()):
    if not any(k in nm for k in ('StartGame', 'Ready', 'P2PInfo')):
        continue
    print()
    print('--- %s @0x%08X ---' % (nm, name_va))
    td_va = name_va          # TypeDescriptor 结构体起始 = name 起始
    print('  TypeDescriptor @0x%08X' % td_va)
    # 向前 8 字节应是 {pVFTable, spare} 或 {spare, pVFTable}
    for off in (-8, -4, 4, 8):
        v = u32_at(td_va + off)
        print('    [%+d] = 0x%08X' % (off, v if v is not None else 0))

    td_rva = td_va - IMG_BASE
    refs = find_u32(td_rva)
    print('  TD RVA 0x%X 被引用 %d 处' % (td_rva, len(refs)))
    done = False
    for r in refs[:8]:
        col_va = r - 12
        col = read_at(col_va, 20)
        if not col:
            continue
        sig, off, cd, ptd, pcd = struct.unpack('<IIIII', col)
        if ptd != td_rva:
            continue
        print('    COL @0x%08X sig=%d off=%d cd=%d pCD=0x%X'
              % (col_va, sig, off, cd, pcd))
        for vtm in find_u32(col_va)[:3]:
            vt_va = vtm + 4
            fns = []
            for k in range(16):
                fn = u32_at(vt_va + k * 4)
                if fn is None or not (0x400000 <= fn < 0x1000000):
                    break
                fns.append(fn)
            print('      vtable @0x%08X (%d 个虚函数)' % (vt_va, len(fns)))
            for k, fn in enumerate(fns):
                print('        [%2d] 0x%08X' % (k, fn))
            done = True
            break
        if done:
            break
    if not done:
        print('    (未解析到)')

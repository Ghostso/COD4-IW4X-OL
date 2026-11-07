"""从内存转储反查 dwRoomMessage* 的 vtable（修正版）。

实测布局（0x00E6F72C 处）：
    +0   spare        (u32, =0)
    +4   pVFTable     (u32) = 0x00D77818  ← 指向 TypeDescriptor 的 vftable
    +8   name[]       "?AVdwRoomMessageStartGameFailed@@"

所以 TypeDescriptor 起点 = name_va - 8，其 pTypeDescriptor 的 VA 就是这个起点。

MSVC 32 位 COL：
    struct CompleteObjectLocator {
        u32 signature;       // 0
        u32 offset;
        u32 cdOffset;
        u32 pTypeDescriptor; // RVA (相对 IMG_BASE)
        u32 pClassDescriptor;
    };
    vtable[-4] 处 = &COL
"""
import os
import struct
import sys

D = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4])

IMG_BASE = 0x400000
DATA = {}


def blob(base):
    if base not in DATA:
        for b, (size, fn) in regions.items():
            if b == base:
                DATA[base] = open(os.path.join(D, fn), 'rb').read()
                break
        else:
            DATA[base] = None
    return DATA[base]


def read_at(va, n):
    for base, (size, fn) in regions.items():
        if base <= va < base + size:
            off = va - base
            if off + n <= size:
                d = blob(base)
                return d[off:off + n] if d else None
    return None


def u32_at(va):
    r = read_at(va, 4)
    return struct.unpack('<I', r)[0] if r else None


def find_u32(val, limit=400):
    pat = struct.pack('<I', val)
    out = []
    for base, (size, fn) in sorted(regions.items()):
        d = blob(base)
        if not d:
            continue
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


TARGETS = [
    ('dwRoomMessageStartGame',       0x00E6F75C),
    ('dwRoomMessageStartGameFailed', 0x00E6F70C),
    ('dwRoomMessageReady',           0x00E6F394),
    ('dwRoomMessageP2PInfo',         0x00E6F33C),
    ('dwRoomImp',                    0x00E6F8A4),
]

for name, name_va in TARGETS:
    print()
    print('===== %s (name @0x%08X) =====' % (name, name_va))
    raw = read_at(name_va, 64)
    if raw:
        nm = raw.split(b'\x00')[0].decode('latin1')
        print('  名字核验: %s' % nm)
    td_va = name_va - 4          # 含 ".?AV" 前缀
    vft = u32_at(td_va + 32)   # name 之后的 pVFTable
    print('  TypeDescriptor @0x%08X  pVFTable=0x%08X' % (td_va, vft or 0))

    td_rva = td_va - IMG_BASE
    refs = find_u32(td_rva) or find_u32(td_va)
    print('  pTypeDescriptor 引用 %d 处' % len(refs))
    found_vt = False
    for r in refs[:6]:
        col_va = r - 12
        col = read_at(col_va, 20)
        if not col:
            continue
        sig, off, cd, ptd, pcd = struct.unpack('<IIIII', col)
        if ptd not in (td_rva, td_va):
            continue
        print('    COL @0x%08X sig=%d off=%d cd=%d pTD=0x%X pCD=0x%X'
              % (col_va, sig, off, cd, ptd, pcd))
        vt_refs = find_u32(col_va)
        for vtm in vt_refs[:3]:
            vt_va = vtm + 4
            fns = []
            for k in range(12):
                fn = u32_at(vt_va + k * 4)
                if fn is None or not (0x400000 <= fn < 0x1000000):
                    break
                fns.append(fn)
            print('    vtable @0x%08X  虚函数 %d 个' % (vt_va, len(fns)))
            for k, fn in enumerate(fns):
                print('       [%2d] 0x%08X' % (k, fn))
            found_vt = True
            break
        if found_vt:
            break
    if not found_vt:
        print('    (未找到 vtable)')

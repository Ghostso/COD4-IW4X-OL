"""批量解析全部 dwRoomMessage* 的 COL 与 vtable。

已验证的单例 (dwRoomMessageStartGame):
  名字 ".?AVdwRoomMessageStartGame@@" @ 0x00E6F75C
  TypeDescriptor @ 0x00E6F754  { pVFTable=0x00D77818, spare=0, name }
  COL @ 0x00DF93B0  { sig=0, off=0, cd=0, pTD=0x00E6F754, pCD=0x00DF93C4 }
  vtable @ 0x00DC7518  (COL 指针在 vtable[-1])

批量做法:
  1. 扫内存找全部 "?AVdwRoomMessage" 得到 name VA
  2. TypeDescriptor = name - 8
  3. 搜引用得到 COL
  4. 搜 COL 引用得到 vtable
"""
import json
import os
import struct

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
OUT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\dwroommsg_vtables_20261027.json'

regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4])

CACHE = {}


def blob(b):
    if b not in CACHE:
        CACHE[b] = open(os.path.join(D, regions[b][1]), 'rb').read()
    return CACHE[b]


def read_at(va, n):
    for base, (size, fn) in regions.items():
        if base <= va < base + size and va + n <= base + size:
            return blob(base)[va - base:va - base + n]
    return None


def u32_at(va):
    r = read_at(va, 4)
    return struct.unpack('<I', r)[0] if r else None


def find_u32(val, limit=40):
    pat = struct.pack('<I', val)
    out = []
    for base in sorted(regions):
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


# 1. 收集所有 dwRoom* 类型名
names = {}
for base in sorted(regions):
    d = blob(base)
    pos = 0
    while True:
        i = d.find(b'?AVdwRoom', pos)
        if i < 0:
            break
        end = d.find(b'\x00', i)
        if end > i and end - i < 120:
            nm = d[i:end].decode('latin1')
            if nm not in names:
                names[nm] = base + i
        pos = i + 1

print('发现 %d 个 dwRoom* 类型名' % len(names))

results = []
for nm, name_va in sorted(names.items()):
    td_va = name_va - 9          # name_va 指向 "?AV", 前面还有 "." 和 8 字节头
    vft = u32_at(td_va)
    spare = u32_at(td_va + 4)
    rec = {'name': nm, 'name_va': name_va, 'td_va': td_va,
           'pVFTable': vft, 'spare': spare}
    if vft != 0x00D77818:
        rec['error'] = 'pVFTable 不匹配'
        results.append(rec)
        continue
    col_refs = find_u32(td_va)
    if not col_refs:
        rec['error'] = 'TD 无引用'
        results.append(rec)
        continue
    col_va = col_refs[0] - 12
    sig, off_, cd, ptd, pcd = [u32_at(col_va + k * 4) for k in range(5)]
    rec['col_va'] = col_va
    rec['col'] = {'sig': sig, 'off': off_, 'cd': cd, 'pTD': ptd, 'pCD': pcd}
    if ptd != td_va:
        rec['error'] = 'COL.pTD 不匹配'
        results.append(rec)
        continue
    vt_refs = find_u32(col_va)
    if not vt_refs:
        rec['error'] = 'COL 无引用'
        results.append(rec)
        continue
    vt_va = vt_refs[0]
    fns = []
    for k in range(24):
        fn = u32_at(vt_va + 4 + k * 4)   # vtable[0] 在 COL 之后
        if fn is None or not (0x400000 <= fn < 0x1000000):
            break
        fns.append(fn)
    rec['vtable_va'] = vt_va + 4
    rec['vfuncs'] = fns
    results.append(rec)

ok = [r for r in results if 'vfuncs' in r]
print('成功解析 %d / %d' % (len(ok), len(results)))
print()
for r in sorted(ok, key=lambda x: x['name'])[:20]:
    print('  %-46s vtable=0x%08X  虚函数=%d'
          % (r['name'][4:], r['vtable_va'], len(r['vfuncs'])))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print()
print('写出 %s' % OUT)

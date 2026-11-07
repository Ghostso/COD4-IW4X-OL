"""从内存转储里恢复每个 dwRoomMessage* 的 type 常量。

依据: 每个消息类的构造器都会写
    mov dword ptr [eax], <vtable>      ; 68 <vtable32> 或 c7 00 <vtable32>
    mov dword ptr [eax + 4], <type>    ; c7 40 04 <type32>
这里直接在转储里搜 `c7 00 <vtable>` 得到构造器基址, 再从那里向后找
`c7 40 04 <imm>` 或 `c7 41 04 <imm>` / `c7 42 04 <imm>` 得到 type。
只读转储。
"""
import json
import os
import struct
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
FIX = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\dwroommsg_vtables_20261027.json'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

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


def find_vtable_stores(vtable):
    """返回所有 `c7 00 <vtable>` / `68 <vtable>` 的位置。"""
    pat_c7 = b'\xc7\x00' + struct.pack('<I', vtable)
    pat_push = b'\x68' + struct.pack('<I', vtable)
    hits = []
    for base, size, fn, prot in regions:
        if not (prot & 0x20 or prot & 0x4 or prot & 0x2):
            continue
        data = blob(fn)
        if len(data) != size:
            continue
        for pat in (pat_c7, pat_push):
            i = data.find(pat)
            while i >= 0:
                hits.append(base + i)
                i = data.find(pat, i + 1)
    return hits


TYPE_STORES = [
    (b'\xc7\x40\x04', 3), (b'\xc7\x41\x04', 3), (b'\xc7\x42\x04', 3),
    (b'\xc7\x43\x04', 3), (b'\xc7\x46\x04', 3), (b'\xc7\x47\x04', 3),
]


def find_type_after(va, window=0x80):
    data = read_at(va, window)
    if not data:
        return None
    best = None
    for pat, off in TYPE_STORES:
        i = data.find(pat)
        if i >= 0 and (best is None or i < best[0]):
            val = struct.unpack_from('<I', data, i + off)[0]
            if 0 < val < 0x400:
                best = (i, val)
    return best[1] if best else None


entries = json.load(open(FIX, encoding='utf-8'))
rows = []
for e in entries:
    name = e['name']
    if not name.startswith('?AVdwRoomMessage'):
        continue
    vt = e['vtable_va']
    stores = find_vtable_stores(vt)
    typ = None
    for s in stores:
        t = find_type_after(s)
        if t is not None:
            typ = t
            break
    rows.append((name.replace('?AV', '').replace('@@', ''), vt, typ,
                 [hex(s) for s in stores[:3]]))

lines = ['# dwRoomMessage* type 常量（由构造器恢复）', '',
         '来源: MEMDUMP_20261027_v4，搜 `c7 00 <vtable>` 定位构造器，',
         '再取其后的 `c7 4x 04 <imm>` 作为 type。', '',
         '| 类 | vtable | type | 构造器证据 |', '|---|---|---|---|']
for name, vt, typ, stores in rows:
    lines.append('| %s | 0x%08X | %s | %s |'
                 % (name, vt, ('0x%02X (%d)' % (typ, typ)) if typ else '?',
                    ', '.join(stores) if stores else '-'))
open(os.path.join(OUT, 'room_msg_types.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
for name, vt, typ, _ in rows:
    if typ:
        print('%-42s type=0x%02X (%d)' % (name, typ, typ))
    else:
        print('%-42s type=? ' % name)

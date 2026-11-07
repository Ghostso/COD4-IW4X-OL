"""从 mp_firingrange_zone.bin 导出完整 clipmap (按 IW4X 结构)。

已验证:
  plane 表   : 5001523 .. 5153263  (7587 项, 20B/项)
  brushside  : 42720480, 18770 项 (8B/项), 指针 delta = 0x2FE4FC1E
  材质字符串 : 42716679 .. 42720473 (285 项)

输出:
  fixtures/mp_firingrange_clipmap.json   完整结构
  include/codol_clipmap_mp_firingrange.h  C 头文件 (brush bounds + contents)
"""
import json
import math
import struct
from pathlib import Path

ROOT = Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
ZONE = ROOT / '_map_extract' / 'mp_firingrange_zone.bin'
OUTJSON = ROOT / 'CODOL_SERVER_319_20261021' / 'fixtures' / 'mp_firingrange_clipmap.json'
OUTHDR = ROOT / 'CODOL_SERVER_319_20261021' / 'include' / 'codol_clipmap_mp_firingrange.h'

PLANES_OFF = 5001523
PLANE_COUNT = 7587
SIDES_OFF = 42720480
SIDE_COUNT = 18770
DELTA = 0x2FE4FC1E

d = ZONE.read_bytes()
N = len(d)


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]
def f32(o): return struct.unpack_from('<f', d, o)[0]


print('读入 %s B' % format(N, ','))

# ---- planes ----
planes = []
for i in range(PLANE_COUNT):
    o = PLANES_OFF + i * 20
    n = struct.unpack_from('<3f', d, o)
    planes.append({'normal': [n[0], n[1], n[2]],
                   'dist': f32(o + 12),
                   'type': d[o + 16]})
print('planes  = %d' % len(planes))

# ---- brushsides ----
sides = []
for i in range(SIDE_COUNT):
    o = SIDES_OFF + i * 8
    p = u32(o)
    idx = (p - DELTA - PLANES_OFF) // 20 if p else -1
    sides.append({'plane': idx,
                  'material': u16(o + 4),
                  'first_adjacent': struct.unpack_from('<b', d, o + 6)[0],
                  'edge_count': struct.unpack_from('<b', d, o + 7)[0]})
print('sides   = %d' % len(sides))

# ---- 找 cbrush_t 表 (36B) ----
# IW4X: cbrush_t { u16 numsides; u16 glassPieceIndex; cbrushside_t* sides;
#                  u8* baseAdjacentSide; u16 axialMaterialNum[2][3];
#                  u8 firstAdjacentSideOffsets[2][3]; u8 edgeCount[2][3]; }
side_lo = min(p for p in (u32(SIDES_OFF + i * 8) for i in range(SIDE_COUNT)) if p)
side_hi = max(p for p in (u32(SIDES_OFF + i * 8) for i in range(SIDE_COUNT)) if p)

cands = []
for o in range(0, N - 36 * 8, 4):
    okc = 0
    ptrhit = 0
    for k in range(8):
        b = o + k * 36
        if b + 36 > N:
            break
        ns = u16(b)
        sp = u32(b + 4)
        if ns <= 64:
            okc += 1
        if sp == 0 or (side_lo <= sp <= side_hi and (sp - DELTA - SIDES_OFF) % 8 == 0):
            ptrhit += 1
    if okc == 8 and ptrhit >= 6:
        cands.append(o)

print('cbrush 候选起点 %d 个: %s' % (len(cands), cands[:10]))

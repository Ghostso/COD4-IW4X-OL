"""定位 clipMap_t 头部: 用 numBrushes=70 作为锚点。

已知:
  mapents 有 70 个 script_brushmodel
  IW4X clipMap_t 布局 (32 位):
    +0  name(ptr)  +4 isInUse  +8 planeCount  +12 planes(ptr)
    +16 numStaticModels  +20 staticModelList
    +24 numMaterials  +28 materials
    +32 numBrushSides  +36 brushsides
    ...
    +?  u16 numBrushes  +? cbrush_t* brushes
    +?  Bounds* brushBounds  +? int* brushContents

策略: 找 u16 numBrushes == 70 且前后有合理指针的位置。
"""
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]


TARGET_BRUSHES = 70

print('=== 搜索 numBrushes == 70 的位置 ===')
hits = []
for o in range(0, N - 8, 2):
    if u16(o) != TARGET_BRUSHES:
        continue
    # 后面紧跟 cbrush_t* brushes
    for delta in (2, 4):
        p = u32(o + delta)
        if 0x30000000 <= p < 0x34000000:
            hits.append((o, delta, p))

print('候选 %d 个' % len(hits))
for o, delta, p in hits[:30]:
    ctx = d[max(0, o - 8):o + 16]
    print('  off=%-10d +%-2d ptr=0x%08X  ctx=%s' % (o, delta, p, ctx.hex(' ')))

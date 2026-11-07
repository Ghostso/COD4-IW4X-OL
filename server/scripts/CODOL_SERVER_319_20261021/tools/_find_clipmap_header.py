"""定位 mp_firingrange_zone 里的 clipMap_t 头部 (256B, align 64)。

IW4X Structs.hpp clipMap_t (offset 单位=字节, 32 位指针):
  +0   const char* name
  +4   int isInUse
  +8   u32 planeCount
  +12  cplane_s* planes
  +16  u32 numStaticModels
  +20  cStaticModel_s* staticModelList
  +24  u32 numMaterials
  +28  ClipMaterial* materials
  +32  u32 numBrushSides
  +36  cbrushside_t* brushsides
  +40  u32 numBrushEdges
  +44  u8* brushEdges
  ...
  +?   u16 numBrushes
  ...
  +?   u32 checksum

策略: 搜索 "planeCount 和 numBrushSides 同时为已知值" 的位置。
已知候选: planeCount=7587, numBrushSides=18770。
但这两个数也是我之前从指针推的, 需要用多种 (planeCount, numBrushSides)
组合扫描, 看是否存在自洽的头部。
"""
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

print('size %s' % format(N, ','))

# 32 位布局: planeCount at +8, numMaterials at +24, numBrushSides at +32
# 指针应为 0x30000000..0x32000000
hits = []
for o in range(0, N - 256, 4):
    pc = struct.unpack_from('<I', d, o + 8)[0]
    pp = struct.unpack_from('<I', d, o + 12)[0]
    nm = struct.unpack_from('<I', d, o + 24)[0]
    mp = struct.unpack_from('<I', d, o + 28)[0]
    nbs = struct.unpack_from('<I', d, o + 32)[0]
    bsp = struct.unpack_from('<I', d, o + 36)[0]
    if not (0 < pc < 100000 and 0 < nbs < 200000 and 0 < nm < 5000):
        continue
    for ptr in (pp, mp, bsp):
        if not (0x30000000 <= ptr < 0x33000000):
            break
    else:
        hits.append((o, pc, nm, nbs, pp, mp, bsp))

print('候选 clipMap_t 头部: %d 个' % len(hits))
for h in hits[:25]:
    off, pc, nm, nbs, pp, mp, bsp = h
    print('  off=%-10d plane=%-6d mat=%-5d sides=%-6d  ptr planes=0x%08X mat=0x%08X sides=0x%08X'
          % (off, pc, nm, nbs, pp, mp, bsp))

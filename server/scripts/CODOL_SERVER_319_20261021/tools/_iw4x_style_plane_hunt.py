"""用 IW4X 的确切结构定位 mp_firingrange 的 clipmap 各表。

IW4X Structs.hpp:
  cplane_s      20B  { float normal[3]; float dist; u8 type; u8 pad[3]; }
  cbrushside_t   8B  { cplane_s* plane; u16 materialNum; i8 fadj; i8 ecnt; }
  cbrush_t      36B  { u16 numsides; u16 glassPieceIndex; cbrushside_t* sides;
                       u8* baseAdjacentSide; u16 axialMaterialNum[2][3];
                       u8 firstAdjacentSideOffsets[2][3]; u8 edgeCount[2][3]; }
  Bounds        24B  { float midPoint[3]; float halfSize[3]; }

已知 (实测):
  sides_off = 42720480, 18770 项, 指针范围 0x30314D51..0x30339D45
  材质字符串表在 42716679..42720473 (285 项)

目标: 定位 planes 表 (7580 项)。
方法: IW4X 的 save() 顺序是 planes -> staticModelList -> materials -> brushsides ...
      所以在 zone 文件里, planes 表应在 **materials 之前**。
      但材质 "字符串" 在 materials 结构之后, 所以 planes 可能在材质字符串之前的某处,
      也可能因为 align 而分离。逐段扫描 20B 对齐的 cplane_s 记录。
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

SIDES = 42720480
MAT_STR = 42716679


def plane_ok(o):
    if o < 0 or o + 20 > N:
        return False
    n = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    for v in n:
        if not math.isfinite(v) or abs(v) > 1.6:
            return False
    if not math.isfinite(dist) or abs(dist) > 200000.0:
        return False
    l2 = n[0]*n[0] + n[1]*n[1] + n[2]*n[2]
    return 0.85 < l2 < 1.15


print('=== 从材质表向前扫描 cplane_s 连续段 ===')
o = MAT_STR
runs = []
while o > 20:
    if plane_ok(o - 20):
        j = o - 20
        cnt = 1
        while plane_ok(j - 20):
            j -= 20
            cnt += 1
        if cnt >= 5:
            runs.append((j, cnt, o))
        o = j
    else:
        o -= 4

print('找到 %d 段' % len(runs))
for start, cnt, end in runs[:15]:
    print('  off=%d count=%d end=%d' % (start, cnt, end))

print()
print('=== 在 200000 距离内 (材质表前) 逐 20B 检查 ===')
good = 0
first = None
for i in range(0, 300000):
    o = MAT_STR - 20 - i * 20
    if o < 0:
        break
    if plane_ok(o):
        good += 1
        if first is None:
            first = o
    else:
        if good >= 10:
            break
        good = 0
        first = None
print('从材质表向前连续合法平面数 = %d, 起点 = %s' % (good, first))

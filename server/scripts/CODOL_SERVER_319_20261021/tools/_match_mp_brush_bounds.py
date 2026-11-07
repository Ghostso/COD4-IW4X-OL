"""用找到的 Bounds 段反推 brush 表。

Bounds 段: off=20772364 count=1054 (最大的一段)
按 IW4X 顺序: brushes -> brushBounds -> brushContents
所以 brush 表在 bounds 之前, 每项 36B, 共 count 项。
但 bounds 前有 ALIGN_128 填充, 所以 brush 表尾不一定紧邻。

验证方法: 从每个候选 brush 段起点, 检查向后第 count 项是否恰好落在 bounds 起点附近。
"""
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

SIDES_OFF = 42720480
SIDE_COUNT = 18770
DELTA = 0x2FE4FC1E
SIDE_LO = DELTA + SIDES_OFF
SIDE_HI = SIDE_LO + SIDE_COUNT * 8
MAT_COUNT = 285

BOUNDS_OFF = 20772364
BOUNDS_CNT = 1054


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]


def brush_ok(o):
    if o < 0 or o + 36 > N:
        return False
    ns = u16(o)
    glass = u16(o + 2)
    sp = u32(o + 4)
    if ns > 64 or glass > 64:
        return False
    if sp:
        if not (SIDE_LO <= sp < SIDE_HI):
            return False
        if (sp - SIDE_LO) % 8:
            return False
        if (sp - SIDE_LO) // 8 + ns > SIDE_COUNT:
            return False
    for k in range(6):
        if u16(o + 12 + k * 2) >= MAT_COUNT:
            return False
    return True


print('=== 找 brush 表起点, 使其 + count*36 对齐到 bounds 起点 ===')
found = []
for pad in range(0, 256, 4):
    cand = BOUNDS_OFF - pad - BOUNDS_CNT * 36
    if cand < 0:
        continue
    # 检查整个表
    if all(brush_ok(cand + i * 36) for i in range(BOUNDS_CNT)):
        found.append(cand)
        print('  命中: brush_off=%d (pad=%d)  count=%d' % (cand, pad, BOUNDS_CNT))

if not found:
    print('  未命中 —— 抽样检查候选起点前若干 brush 合法性:')
    for pad in (0, 124, 128, 252, 256):
        cand = BOUNDS_OFF - pad - BOUNDS_CNT * 36
        if cand < 0:
            continue
        ok = sum(1 for i in range(min(50, BOUNDS_CNT)) if brush_ok(cand + i * 36))
        print('    pad=%-4d off=%-10d 前50项合法=%d/50' % (pad, cand, ok))

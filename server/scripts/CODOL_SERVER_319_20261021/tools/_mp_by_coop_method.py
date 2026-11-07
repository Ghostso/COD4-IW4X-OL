"""把 coop 的 clipmap 解析器套用到 mp_firingrange_zone.bin。

coop 的成功定位方式 (export_clipmap_zone.py):
  MAT_BLOB = b'clip_player\x00clip_shot_block\x00clip_full\x00clip\x00'
  从 material 字符串表反推:
    mats_off   = mat_strings - 4*12      (4 项 ClipMaterial, 每项 12B)
    sides_off  = mat_strings + len(MAT_BLOB)
    planes_off = mats_off - n_planes*20  (向前回溯连续 cplane_s)
    header     = planes_off - 64

mp_firingrange 的材质表是 285 项 (不是 4 项), 且名字不同,
所以 MAT_BLOB 要换。先找它自己的材质字符串起点,
然后按 285 项反推 mats_off = mat_strings - 285*12。
"""
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

MAT_STR = 42716679      # 已定位: 材质名字符串起点 (clip_full ...)
MAT_COUNT = 285


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]
def f32(o): return struct.unpack_from('<f', d, o)[0]

print('=== 按 coop 的思路反推 mp 的 clipmap ===')
print('material 字符串表起点 = %d' % MAT_STR)

# ClipMaterial 12B/项, 在字符串表之前
mats_off = MAT_STR - MAT_COUNT * 12
print('mats_off = %d - %d*12 = %d' % (MAT_STR, MAT_COUNT, mats_off))
print()

print('=== 检查 mats_off 处是否像 ClipMaterial 数组 ===')
for i in range(min(6, MAT_COUNT)):
    o = mats_off + i * 12
    surf = struct.unpack_from('<i', d, o + 4)[0]
    cont = u32(o + 8)
    print('  mat[%d] ptr=0x%08X surface=%d contents=0x%08X'
          % (i, u32(o), surf, cont))

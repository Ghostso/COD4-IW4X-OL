"""从 18770 个 brushside 指针反推 plane 表位置。

已知:
  sides_off = 42720480, 每项 8B = (u32 plane_ptr, u16 material, i8 fadj, i8 ecnt)
  ptr 范围 0x30000000..0x32000000

思路: 所有 plane_ptr 应满足 ptr = PLANE_BASE + index*20。
  => 相邻两指针之差应为 20 的倍数。
找出 ptr 集合的最小值, 它对应 index 0 (或接近)。
"""
import struct
from collections import Counter

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

SIDES = 42720480
ptrs = []
o = SIDES
while o + 8 <= N:
    p = struct.unpack_from('<I', d, o)[0]
    if not (0x30000000 <= p < 0x32000000):
        break
    ptrs.append(p)
    o += 8

print('brushside 数 = %d' % len(ptrs))
if not ptrs:
    raise SystemExit

uniq = sorted(set(ptrs))
print('不同指针值 = %d' % len(uniq))
print('最小 = 0x%08X   最大 = 0x%08X   跨度 = %d (0x%X)'
      % (uniq[0], uniq[-1], uniq[-1] - uniq[0], uniq[-1] - uniq[0]))
print('跨度 / 20 = %d' % ((uniq[-1] - uniq[0]) / 20))
print()

# 相邻差值的模 20 分布
diffs = [uniq[i+1] - uniq[i] for i in range(len(uniq) - 1)]
mods = Counter(x % 20 for x in diffs)
print('相邻指针差 % 20 的分布:', dict(mods))
print()

# 假设 base = uniq[0] - k*20 之一, 找一个让所有 (ptr-base) % 20 == 0 的 base
for k in range(0, 20):
    base = uniq[0] - k * 20
    ok = all((p - base) % 20 == 0 for p in uniq)
    if ok:
        print('base = 0x%08X (k=%d): 所有指针 % 20 == 0  [OK]' % (base, k))
        print('  => plane 表所在虚拟偏移 = 0x%08X' % base)
        print('  最大索引 = %d' % ((uniq[-1] - base) // 20))
        break
else:
    print('无法得到一致的 base —— 指针可能不是连续数组')
    print('前 10 个不同指针:')
    for p in uniq[:10]:
        print('  0x%08X' % p)

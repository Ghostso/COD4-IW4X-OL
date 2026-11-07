"""求 mp_firingrange 的 plane 表：虚拟指针 -> 文件偏移 的 delta。

已知:
  plane_ptr 最小值 = 0x30314D51, 步长 20, 索引 0..7577
  文件里一定存在一段 7580 项的 cplane_t 表

方法: 扫描文件里所有 "连续 20B 合法平面" 的起点, 对每个候选起点 C,
      计算 delta = 0x30314D51 - C, 然后检验 "所有指针是否都落在 C..C+count*20"。
"""
import math
import struct

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
uniq = sorted(set(ptrs))
BASE_VADDR = uniq[0]
MAXIDX = (uniq[-1] - BASE_VADDR) // 20

print('指针 %d 个, 索引 0..%d' % (len(ptrs), MAXIDX))


def plane_at(o):
    if o < 0 or o + 20 > N:
        return None
    n = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    if not all(math.isfinite(v) for v in n) or not math.isfinite(dist):
        return None
    l2 = n[0]*n[0] + n[1]*n[1] + n[2]*n[2]
    if abs(l2 - 1.0) < 0.02 and abs(dist) < 200000.0:
        return (n, dist)
    return None


# 先看现有 scan 找到的那几段 (off=5294604 等) 附近的平面表规模
print()
print('=== 检查已知平面段附近的规模 ===')
for cand in (5294604, 5294924, 5300640, 5303276):
    cnt = 0
    while plane_at(cand + cnt * 20):
        cnt += 1
    # 向前扩展
    back = 0
    while plane_at(cand - (back + 1) * 20):
        back += 1
    start = cand - back * 20
    total = cnt + back
    print('  候选 %d: 前扩 %d, 后 %d, 合计 %d 项  (起点 %d)'
          % (cand, back, cnt, total, start))
    if total >= 100:
        print('    -> 规模足够, 检验指针...')
        delta = BASE_VADDR - start
        hit = sum(1 for p in ptrs
                  if 0 <= (p - delta - start) and (p - delta - start) % 20 == 0
                  and (p - delta - start) // 20 <= MAXIDX)
        print('    delta=0x%X  指针可解析 %d/%d' % (delta, hit, len(ptrs)))

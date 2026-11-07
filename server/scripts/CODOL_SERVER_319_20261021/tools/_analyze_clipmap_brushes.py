"""按 CoD4X 的 brush 规则重新审视我们导出的 clipmap 数据。

CoD4X cm_load_obj.cpp:
    outnumsides = numinsides - 6 * brushcount
    outBrush->numsides = inBrush->numSides - 6

即: BSP 数据里每个 brush 只存"非轴向面", 轴向的 6 个面由引擎隐含。
我们要判断: 导出脚本是不是把这 6 个隐含面丢掉了。
"""
import json

P = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\coop_train_clipmap_20261023.json'
j = json.load(open(P, encoding='utf-8'))
br = j['brushes']
planes = j['planes']
sides = j['sides']

print('brush=%d  plane=%d  side=%d' % (len(br), len(planes), len(sides)))
print('各 brush numsides 之和 = %d' % sum(b['numsides'] for b in br))
print()

print('=== 每个 brush 的存储面数 vs CoD4X 隐含 +6 ===')
for i, b in enumerate(br):
    n = b['numsides']
    mid = b['bounds']['mid']
    half = b['bounds']['half']
    stored = 'plane-backed' if b['side_first'] is not None else 'AABB only'
    print('  brush[%2d] numsides=%d  +6=%2d  %-12s mid=(%6.0f,%6.0f,%6.0f) half=(%4.0f,%4.0f,%4.0f)'
          % (i, n, n + 6, stored, mid[0], mid[1], mid[2], half[0], half[1], half[2]))
print()

print('=== 27 个平面的法线 Z 分量 ===')
nz_nonzero = sum(1 for p in planes if abs(p['normal'][2]) > 1e-6)
print('  normal.z != 0 的平面数 = %d / %d' % (nz_nonzero, len(planes)))
print('  => 全部为垂直面, 无水平面(地板)' if nz_nonzero == 0 else '  => 存在水平面')

print()
print('=== 结论 ===')
print('  CoD4X 规则说明轴向 6 面是隐含的, 不存盘。')
print('  我们的 AABB (bounds mid/half) 恰好就是这 6 个隐含面构成的盒子。')
print('  也就是说: 每个 brush 的**实体区域**是已知的 (AABB),')
print('  只有"斜面"需要额外平面数据 —— 而我们只有 27 个斜面。')

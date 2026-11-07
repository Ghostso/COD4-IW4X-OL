"""把运行期 dump 与重建 PE 逐区域逐字节比对, 报告:
   - 有多少字节一致 / 有多少不同
   - 不在 PE 镜像范围内的区域(=进程里其它东西: 堆/DLL/匿名映射)—— 这些才是
     "调用者可能不在我重建的 PE 里"这一假设的落脚点
   - 差异最集中的 VA 区间(只报前 30 段)

用法: python -I dump_vs_pe.py <exe> <regions.txt> <dump_dir>
"""
import sys, os
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

exe, regf, ddir = sys.argv[1], sys.argv[2], sys.argv[3]
d, ib, secs = load(exe)
print('PE ImageBase=0x%08X, 文件 %d 字节' % (ib, len(d)))
ranges = [(ib + v, ib + v + max(vs, rs)) for v, vs, ra, rs in secs]
print('PE 镜像范围: %s' % ', '.join('[0x%08X,0x%08X)' % r for r in ranges))

regs = []
for ln in open(regf):
    ln = ln.strip()
    if not ln or ln.startswith('#'):
        continue
    p = ln.split()
    regs.append((int(p[0], 16), int(p[1], 16), p[2]))

same = diff = outside = 0
outside_regs = []
diff_runs = []

for b, s, f in regs:
    fp = os.path.join(ddir, f)
    if not os.path.exists(fp):
        continue
    blob = open(fp, 'rb').read()
    inpe = sum(max(0, min(b + s, hi) - max(b, lo)) for lo, hi in ranges)
    outside += (s - inpe)
    if inpe < s * 0.5:
        outside_regs.append((b, s, f, inpe))
    for i in range(0, min(s, len(blob))):
        va = b + i
        off = va2off(secs, ib, va)
        if off is None or off >= len(d):
            continue
        if blob[i] == d[off]:
            same += 1
        else:
            diff += 1
            if diff_runs and diff_runs[-1][0] + diff_runs[-1][1] == va:
                diff_runs[-1][1] += 1
            else:
                diff_runs.append([va, 1])

print('\n与 PE 重叠并逐字节比过: 一致 %d, 不同 %d (%.3f%% 不同)'
      % (same, diff, 100.0 * diff / max(1, same + diff)))
print('完全不在 PE 镜像范围内的字节: %d (%.1f MB) —— 分属 %d 个区域'
      % (outside, outside / 1048576.0, len(outside_regs)))
print('\n不属 PE 的主要区域(前 30, 按大小):')
for b, s, f, inp in sorted(outside_regs, key=lambda x: -x[1])[:30]:
    print('   0x%08X + 0x%-8X (%.2f MB) PE内%d  %s' % (b, s, s / 1048576.0, inp, f))

diff_runs.sort(key=lambda x: -x[1])
print('\n最大差异段(前 30):')
for va, n in diff_runs[:30]:
    print('   0x%08X  长度 0x%X (%d)' % (va, n, n))

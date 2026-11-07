"""在 dump 的所有区域里搜给定字节模式, 报告绝对 VA。
   用来回答: "我们重建的 PE 里的那段代码, 运行期到底在不在内存里、在哪个地址"。

用法: python -I dump_search.py <regions.txt> <dump_dir> <hex1> [hex2 ...]
"""
import sys, os
sys.path.insert(0, __file__.rsplit('\\', 1)[0])

regf, ddir = sys.argv[1], sys.argv[2]
pats = [(p, bytes.fromhex(p)) for p in sys.argv[3:]]

regs = []
for ln in open(regf):
    ln = ln.strip()
    if not ln or ln.startswith('#'):
        continue
    p = ln.split()
    regs.append((int(p[0], 16), int(p[1], 16), p[2]))

print('区域 %d 个' % len(regs))
for hx, pat in pats:
    print('\n### 模式 %s (%d 字节) ###' % (hx, len(pat)))
    total = 0
    for b, s, f in regs:
        fp = os.path.join(ddir, f)
        if not os.path.exists(fp):
            continue
        blob = open(fp, 'rb').read()
        i = blob.find(pat)
        while i >= 0:
            print('   命中 @ 绝对VA 0x%08X  (区域 0x%08X+0x%X, 区内 0x%X)'
                  % (b + i, b, s, i))
            total += 1
            if total > 12:
                break
            i = blob.find(pat, i + 1)
        if total > 12:
            break
    if total == 0:
        print('   ★ 全 dump 未命中')

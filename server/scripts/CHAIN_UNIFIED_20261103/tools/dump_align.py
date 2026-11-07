"""把重建 PE 与运行期 dump 对齐:
   1) 打印 PE ImageBase / 节表
   2) 对给定 VA, 找它落在哪个 dump 区域(按 相对RVA 或 绝对VA 两种假设各试一次)
   3) 若找到, 逐字节比对 PE 与 dump 在该处的字节, 报告是否一致

用法: python -I dump_align.py <exe> <regions.txt> <dump_dir> 0xBB45E0 [0xBB45F0 ...]
"""
import sys, os, struct
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

exe, regf, ddir = sys.argv[1], sys.argv[2], sys.argv[3]
vas = [int(a, 16) for a in sys.argv[4:]]
d, ib, secs = load(exe)
print('PE ImageBase = 0x%08X' % ib)
print('节表:')
for va_, vs, ra, rs in secs:
    print('   rva=0x%08X vsize=0x%08X raw=0x%08X rsize=0x%08X' % (va_, vs, ra, rs))

regs = []
for ln in open(regf):
    ln = ln.strip()
    if not ln or ln.startswith('#'):
        continue
    p = ln.split()
    regs.append((int(p[0], 16), int(p[1], 16), p[2]))
print('\ndump 区域 %d 个, 覆盖 [0x%08X, 0x%08X)' % (len(regs), regs[0][0], max(b + s for b, s, _ in regs)))

tot = sum(s for _, s, _ in regs)
print('dump 总字节 %d (%.1f MB)' % (tot, tot / 1048576.0))


def reg_of(addr):
    for b, s, f in regs:
        if b <= addr < b + s:
            return b, s, f
    return None


for va in vas:
    rva = va - ib
    off = va2off(secs, ib, va)
    print('\n=== VA 0x%08X (RVA 0x%08X, PE文件偏移 %s) ===' % (va, rva, hex(off) if off is not None else 'None'))
    for label, addr in (('按 RVA 找', rva), ('按 绝对VA 找', va)):
        r = reg_of(addr)
        if not r:
            print('  %s: 没有覆盖 -> 未 dump' % label)
            continue
        b, s, f = r
        fp = os.path.join(ddir, f)
        if not os.path.exists(fp):
            print('  %s: 区域 0x%08X+0x%X 文件 %s 不存在' % (label, b, s, f))
            continue
        blob = open(fp, 'rb').read()
        rel = addr - b
        db = blob[rel:rel + 32]
        pb = d[off:off + 32] if off is not None else b''
        same = (db == pb)
        print('  %s: 区域 0x%08X+0x%X (%s), 区内偏移 0x%X' % (label, b, s, f, rel))
        print('     dump: %s' % db.hex(' '))
        print('     PE  : %s' % pb.hex(' '))
        print('     一致: %s' % ('是' if same else '★否'))
        break

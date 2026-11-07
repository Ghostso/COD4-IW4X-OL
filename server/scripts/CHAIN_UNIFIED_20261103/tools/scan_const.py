"""字节级常量扫描: 在整镜像里找 u32 立即数(小端)的所有出现位置, 并反汇编窗口。

用法:
  python -I scan_const.py 0xD5AFA4
  python -I scan_const.py 0xD5AFA4 --ctx 24 --limit 60
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

val = int(sys.argv[1], 0)
ctx = 24
limit = 200
for i, a in enumerate(sys.argv):
    if a == '--ctx' and i + 1 < len(sys.argv):
        ctx = int(sys.argv[i + 1], 0)
    if a == '--limit' and i + 1 < len(sys.argv):
        limit = int(sys.argv[i + 1], 0)

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

raw = val.to_bytes(4, 'little')
hits = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    blob = d[ra:ra + n]
    i = blob.find(raw)
    while i >= 0:
        hits.append(ib + va_ + i)
        i = blob.find(raw, i + 1)

print('0x%08X 出现 %d 次' % (val, len(hits)))
for addr in hits[:limit]:
    print('--- %08X' % addr)
    off = addr - ib - ctx
    try:
        for ins in md.disasm(d[off:addr - ib + 8], addr - ctx):
            mark = '  <<<' if ins.address <= addr < ins.address + ins.size else ''
            print('      %08X  %-10s %s%s' % (ins.address, ins.mnemonic, ins.op_str, mark))
    except Exception as e:
        print('      <disasm error %s>' % e)

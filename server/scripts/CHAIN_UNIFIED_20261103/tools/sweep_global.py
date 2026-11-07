"""Linear-sweep the unpacked PE and list every instruction referencing a global address.
   usage: python -I sweep_global.py 0x076446B0 [--writes]
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load
import capstone

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

target = sys.argv[1].lower().replace('0x', '')
writes_only = '--writes' in sys.argv
CHUNK = 1 << 16
OVER = 16
seen = set()
rows = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    base = ib + va_
    pos = 0
    while pos < n:
        end = min(pos + CHUNK, n)
        seg = d[ra + pos: ra + end]
        for ins in md.disasm(seg, base + pos):
            if ins.address in seen:
                continue
            seen.add(ins.address)
            if target in ins.op_str.lower():
                is_write = False
                dst = ins.op_str.split(',')[0].strip()
                if '[' in dst:
                    if ins.mnemonic == 'mov':
                        is_write = True
                    elif ins.mnemonic in ('add', 'sub', 'or', 'and', 'xor', 'inc', 'dec',
                                          'shl', 'sar', 'shr'):
                        is_write = True
                if writes_only and not is_write:
                    continue
                rows.append((ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))
        pos = end - OVER if end < n else end
for r in sorted(rows):
    print('%08X %-24s %s %s' % (r[0], r[1], r[2], r[3]))
print('total %d' % len(rows))

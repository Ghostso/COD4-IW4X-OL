"""Find every code reference to a global VA and show the surrounding instruction."""
import sys, struct
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
import capstone

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

def off2va(off):
    for va_, vs, ra, rs in secs:
        if ra <= off < ra + min(vs, rs):
            return ib + va_ + (off - ra)
    return None

target = int(sys.argv[1], 16)
pat = struct.pack('<I', target)
hits = []
s = 0
while True:
    i = d.find(pat, s)
    if i < 0:
        break
    s = i + 1
    va = off2va(i)
    if va is not None:
        hits.append(va)

print('refs to %08X: %d' % (target, len(hits)))
for va in hits:
    start = va - 12
    off = va2off(secs, ib, start)
    if off is None:
        continue
    code = d[off:off + 24]
    line = []
    for ins in md.disasm(code, start):
        mark = '>>' if ins.address <= va < ins.address + ins.size else '  '
        line.append('%s%08X %-20s %s %s' % (mark, ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))
    print('\n'.join(line))
    print('-' * 60)

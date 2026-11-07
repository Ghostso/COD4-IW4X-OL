"""原始字节模式扫描(整镜像), 输出命中 VA 与对齐反汇编窗口。

用法:
  python -I scan_pat.py 8b88f0010000                 # mov ecx,[eax+0x1F0]
  python -I scan_pat.py 8b88f0010000 --ctx 20 --limit 40
  python -I scan_pat.py --any 8b80f0010000 8b88f0010000 8b90f0010000
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

args = sys.argv[1:]
pats = []
if '--any' in args:
    i = args.index('--any')
    for a in args[i + 1:]:
        if a.startswith('--'):
            break
        pats.append(bytes.fromhex(a))
else:
    pats.append(bytes.fromhex(args[0]))

ctx = 24
limit = 200
for i, a in enumerate(args):
    if a == '--ctx' and i + 1 < len(args):
        ctx = int(args[i + 1], 0)
    if a == '--limit' and i + 1 < len(args):
        limit = int(args[i + 1], 0)

hits = []
for pat in pats:
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = blob.find(pat)
        while i >= 0:
            hits.append((ib + va_ + i, pat.hex(), va_))
            i = blob.find(pat, i + 1)

hits.sort()
print('%s : %d 处' % (' | '.join(p.hex() for p in pats), len(hits)))


def aligned_window(addr, back):
    """从 addr-back 起尝试所有起点, 选一条能**恰好走到 addr**的反汇编。"""
    off0 = va2off(secs, ib, addr - back)
    offa = va2off(secs, ib, addr)
    if off0 is None or offa is None:
        return None
    for s in range(back):
        start = addr - s
        o = va2off(secs, ib, start)
        if o is None:
            continue
        ins = []
        ok = False
        try:
            for i in md.disasm(d[o:offa], start):
                ins.append(i)
                if i.address + i.size == addr:
                    ok = True
                    break
        except Exception:
            continue
        if ok and ins:
            return start, ins
    return None


for addr, pat, secva in hits[:limit]:
    print('--- %08X  %s' % (addr, pat))
    aw = aligned_window(addr, max(ctx, 20))
    if aw:
        start, ins = aw
        for i in ins:
            print('      %08X  %-30s %s' % (i.address, i.bytes.hex(' '), i.op_str))
    else:
        off = va2off(secs, ib, addr - ctx)
        print('      (未对齐) 原始字节: %s' % d[addr - ib - ctx:addr - ib + 16].hex(' '))

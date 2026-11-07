"""对给定地址做**对齐保证**的上下文反汇编。
   对每个目标地址, 尝试 [addr-maxback, addr) 内所有起始偏移, 选一条**恰好走到 addr**
   且指令数最多(通常是唯一正确对齐)的反汇编。用于看"这条 call 上一句是从哪取的对象"。

用法:
  python -I dis_at.py 0x467 99F 0x46983B ...
  python -I dis_at.py --n 8 0x622128
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
import capstone

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

args = [a for a in sys.argv[1:]]
nlines = 8
if '--n' in args:
    i = args.index('--n')
    nlines = int(args[i + 1])
    del args[i:i + 2]

MAXBACK = 192


def window(addr):
    offa = va2off(secs, ib, addr)
    if offa is None:
        return None
    best = None
    for s in range(2, MAXBACK):
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
                if i.address + i.size > addr:
                    break
        except Exception:
            continue
        if ok and (best is None or len(ins) > len(best[1])):
            best = (start, ins)
    return best


for a in args:
    addr = int(a, 16)
    w = window(addr)
    print('=== %08X ===' % addr)
    if not w:
        print('   (对不齐)')
        continue
    start, ins = w
    for i in ins[-nlines:]:
        print('   %08X  %-22s %-8s %s' % (i.address, i.bytes.hex(' '), i.mnemonic, i.op_str))
    print()

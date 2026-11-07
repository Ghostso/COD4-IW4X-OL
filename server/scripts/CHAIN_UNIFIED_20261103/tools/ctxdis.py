"""对齐感知的上下文反汇编: 给一个 VA, 先向前找函数起点(填充字节/RET 之后),
再线性反汇编到 VA + tail。用于分析 "call [reg+SLOT]" 这类虚调用点的对象来源。

用法:
  python -I ctxdis.py 0x622040
  python -I ctxdis.py 0x622040 --back 120 --tail 40
  python -I ctxdis.py 0x622040 --list 0x622040 0x6221C5 ...
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True


def find_start(va, maxback=0x800):
    """向前找函数起点: 最近的一串 0xCC/0x90 填充之后的第一个字节, 或 RET 之后。"""
    off = va2off(secs, ib, va)
    best = None
    i = 1
    while i < maxback:
        b = d[off - i]
        if b in (0xCC, 0x90, 0x00):
            j = i
            while j < maxback and d[off - j] in (0xCC, 0x90, 0x00):
                j += 1
            cand = va - j + 1
            # 验证: 从 cand 反汇编能恰好到达 va
            start_off = va2off(secs, ib, cand)
            n = off - start_off
            if n > 0:
                last = None
                ok = False
                for ins in md.disasm(d[start_off:off], cand):
                    if ins.address + ins.size == va:
                        ok = True
                    last = ins
                if ok:
                    return cand
            i = j
            continue
        i += 1
    return va - min(maxback, 0x100)


def show(va, back=0, tail=32, label=''):
    start = find_start(va) if back is None else va - back
    off = va2off(secs, ib, start)
    n = (va - start) + tail
    if label:
        print('=== %s ===' % label)
    print('--- 起点 %08X (目标 %08X) ---' % (start, va))
    for ins in md.disasm(d[off:off + n], start):
        mark = '   <<<<' if ins.address <= va < ins.address + ins.size else ''
        print('%08X  %-20s %-8s %s%s' % (ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str, mark))


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--list' in args:
        i = args.index('--list')
        for a in args[i + 1:]:
            show(int(a, 16), None, 8)
            print()
    else:
        va = int(args[0], 16)
        back = None
        tail = 32
        if '--back' in args:
            back = int(args[args.index('--back') + 1], 0)
        if '--tail' in args:
            tail = int(args[args.index('--tail') + 1], 0)
        show(va, back, tail)

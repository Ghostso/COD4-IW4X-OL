"""函数体转储（只读）：从给定 RVA 线性解码，逐条注释
  * `call dword ptr [imm32]` -> .idata2 槽名 (dll!api)
  * 绝对操作数 0x1xxxxxxx    -> 若落在 .idata2 槽则标名，若是可读字符串则内联
用法:
    python scripts/netfunc.py <hexrva> [n_insn] [more_rva ...]
例:
    python scripts/netfunc.py 0x00425370 260
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import importmap
import x86callers as X

IMAGE_BASE = 0x10000000
ABS = re.compile(r'0x([0-9a-f]{8})')


def looks_str(s):
    if not s or len(s) < 4:
        return False
    good = sum(1 for ch in s if 32 <= ord(ch) < 127)
    return good >= len(s) * 0.85


def dump(img, slots, start, n):
    for ins in X.dis(img, start, 15 * n):
        m, ops = ins.mnemonic, ins.op_str
        note = ''
        if m == 'call' and ops.startswith('dword ptr [0x'):
            r = int(ops[13:-1], 16) - IMAGE_BASE
            note = '   ; <- %s' % slots.get(r, 'slot!0x%06x' % r)
        else:
            for mm in ABS.finditer(ops):
                v = int(mm.group(1), 16)
                if not (IMAGE_BASE <= v < IMAGE_BASE + 0x3991000):
                    continue
                r = v - IMAGE_BASE
                if r in slots:
                    note += '   ; [%s]' % slots[r]
                else:
                    try:
                        s = img.cstr(r, 80)
                    except Exception:
                        s = None
                    if looks_str(s):
                        note += '   ; "%s"' % s
        print('  %08x  %-20s %-34s%s' % (ins.address, ins.bytes.hex(),
                                          '%s %s' % (m, ops), note))
        n -= 1
        if n <= 0:
            break


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    n = 260
    starts = []
    for a in args:
        try:
            starts.append(int(a, 16))
        except ValueError:
            n = int(a)
    img = Image()
    slots = importmap.build(img)
    for s in starts:
        print('=' * 78)
        print('## func 0x%08x' % s)
        print('=' * 78)
        dump(img, slots, s, n)
        print('')


if __name__ == '__main__':
    main()

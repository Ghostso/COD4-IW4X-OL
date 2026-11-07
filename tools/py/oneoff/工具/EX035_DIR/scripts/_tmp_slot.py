"""临时（只读）：给若干 IAT 槽地址查 DLL!函数名；并反汇编若干辅助函数。

用法: python scripts/_tmp_slot.py
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000

SLOTS = [
    0x10b0221c, 0x10b02224, 0x10b023b4, 0x10b023bc,
    0x10b02a5c, 0x10b02a60, 0x10b02a64, 0x10b02a68, 0x10b02a6c, 0x10b02a70,
]

DIS = [
    (0x104530e0, 0x10453160),
    (0x10291880, 0x10291900),
    (0x10235b20, 0x10235b80),
    (0x10235a50, 0x10235ab0),
]


def main():
    img = Image()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    # IAT 槽：读 4 字节 -> 若落在 .rdata 内则指向 IMAGE_IMPORT_BY_NAME(HINT+NAME)
    for s in SLOTS:
        v = img.read(s - IMAGE_BASE, 4)
        if not v:
            print('0x%08x  <read failed>' % s)
            continue
        rva = int.from_bytes(v, 'little')
        name = img.cstr(rva - IMAGE_BASE, 64) if rva else None
        print('0x%08x -> rva 0x%08x  %r' % (s, rva, name))
    print()

    for (lo, hi) in DIS:
        print('--- disasm 0x%08x - 0x%08x' % (lo, hi))
        buf = img.read(lo - IMAGE_BASE, hi - lo)
        if not buf:
            print('    <read failed>')
            continue
        i = 0
        while i < len(buf):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(buf[i:], lo + i):
                got = (addr - (lo + i)) + size
                print('  %08x  %-10s %s' % (addr, mn, ops))
            if got == 0:
                i += 1
            else:
                i += got
        print()


if __name__ == '__main__':
    main()

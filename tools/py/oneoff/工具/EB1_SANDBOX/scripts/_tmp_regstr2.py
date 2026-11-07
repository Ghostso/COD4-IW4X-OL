"""临时（只读）：regstr.txt 的四个「0 条串引用」区间需要更宽窗口复扫，
并全量反汇编唯一仍未归属的 0x235xxx 事件驱动客户端簇。

用途：回答"是否存在游戏自己的网络栈"。regstr.txt 已把其余 17 簇全部判为
OpenSSL BIO / libcurl（两份版本），只剩 0x235xxx / 0x6160xx / 0x686cxx /
0x6a60xx 四处 0 命中——窗口过窄或是无关紧要的桩。

用法: python scripts/_tmp_regstr2.py
输出: scripts/_out/regstr2.txt
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000
RD_HI = IMAGE_BASE + 0x009af000
RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')

# 放宽到 ±0xc00 的窗口重扫
RESCAN = [
    ('0x235xxx 事件驱动客户端', 0x235000, 0x236e00),
    ('0x6160xx WSAStartup',     0x615400, 0x616e00),
    ('0x686cxx ioctlsocket',    0x686000, 0x687400),
    ('0x6a60xx gethostname',    0x6a5400, 0x6a6e00),
]

# 全量反汇编（RVA）
DIS = [
    (0x235c00, 0x236200),
    (0x616000, 0x616100),
    (0x686c00, 0x686d00),
    (0x6a6000, 0x6a6100),
]


def main():
    img = Image()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'regstr2.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    for (label, lo_rva, hi_rva) in RESCAN:
        lo = IMAGE_BASE + lo_rva
        hi = IMAGE_BASE + hi_rva
        buf = img.read(lo_rva, hi - lo)
        if not buf:
            P('### %s -> 读取失败' % label)
            continue
        seen = []
        i = 0
        n = len(buf)
        while i < n:
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(buf[i:], lo + i):
                got = (addr - (lo + i)) + size
                for m in RE_IMM.finditer(ops):
                    v = int(m.group(1), 16)
                    if RD_LO <= v < RD_HI:
                        s = img.cstr(v - IMAGE_BASE, 80)
                        if s and s.strip():
                            seen.append((addr, v, s))
            if got == 0:
                i += 1
            else:
                i += got
        P('### %s (0x%08x-0x%08x, %d 条)' % (label, lo, hi, len(seen)))
        prev = None
        shown = 0
        for (a, v, s) in seen:
            if s == prev:
                continue
            prev = s
            P('    @0x%08x  0x%08x  %r' % (a, v, s))
            shown += 1
            if shown >= 60:
                P('    ... (截断)')
                break
        P()

    for (lo_rva, hi_rva) in DIS:
        lo = IMAGE_BASE + lo_rva
        hi = IMAGE_BASE + hi_rva
        P('--- disasm 0x%08x - 0x%08x' % (lo, hi))
        buf = img.read(lo_rva, hi - lo)
        if not buf:
            P('    <read failed>')
            continue
        i = 0
        while i < len(buf):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(buf[i:], lo + i):
                got = (addr - (lo + i)) + size
                P('  %08x  %-10s %s' % (addr, mn, ops))
            if got == 0:
                P('  %08x  <bad byte>' % (lo + i))
                i += 1
            else:
                i += got
        P()
    out.close()
    print('-> scripts/_out/regstr2.txt')


if __name__ == '__main__':
    main()

"""临时（只读）：列出每个目标函数体内**指令边界合法**的 .rdata 字符串引用。

用途 = 归属判据。函数体内引用的字符串是哪个库的文案，函数就属于哪个库。
这比"地址空间位置"可靠：用户明确禁止按地址相邻猜用途。

用法: python scripts/_tmp_fstrings.py
输出: scripts/_out/fstrings.txt
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000
RD_HI = IMAGE_BASE + 0x009af000
RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')

TARGETS = [
    ('A socket 封装',        0x10425370),
    ('A connect/singleip',   0x10425530),
    ('A ?',                  0x1042d930),
    ('A ?',                  0x1042c910),
    ('A ?',                  0x1042cc70),
    ('A bind+listen 宿主',   0x10431460),
    ('A getaddrinfo 包装',   0x1044b240),
    ('A inet_ntop 包装',     0x1044d060),
    ('A inet_ntop 核心',     0x1044cfc0),
    ('B socket 封装',        0x10650900),
    ('B connect/singleip',   0x10650ac0),
    ('B ?',                  0x10670d50),
    ('B ?',                  0x1066fea0),
    ('B ?',                  0x10670120),
    ('B bind+listen 宿主',   0x106747c0),
    ('B getaddrinfo 包装',   0x1065fca0),
]

SPAN = 0x1800


def main():
    img = Image()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'fstrings.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    for (label, va) in TARGETS:
        buf = img.read(va - IMAGE_BASE, SPAN)   # pe.Image.read 收 RVA
        if not buf:
            P('### 0x%08x  %s  -> 读取失败' % (va, label))
            continue
        seen = []
        i = 0
        n = len(buf)
        while i < n:
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(buf[i:], va + i):
                got = (addr - (va + i)) + size
                for m in RE_IMM.finditer(ops):
                    v = int(m.group(1), 16)
                    if RD_LO <= v < RD_HI:
                        s = img.cstr(v - IMAGE_BASE, 72)
                        if s and s.strip():
                            seen.append((addr, v, s, mn + ' ' + ops))
            if got == 0:
                i += 1
            else:
                i += got
        P('### 0x%08x  %s   (扫描 0x%x 字节, %d 条字符串引用)'
          % (va, label, SPAN, len(seen)))
        prev = None
        for (a, v, s, txt) in seen:
            if s == prev:
                continue
            prev = s
            P('    @0x%08x  0x%08x  %r' % (a, v, s))
        P()
    out.close()
    print('-> scripts/_out/fstrings.txt')


if __name__ == '__main__':
    main()

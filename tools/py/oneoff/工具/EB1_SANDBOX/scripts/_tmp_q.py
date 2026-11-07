"""临时（只读）：定点查询 —— 打印若干 .rdata 串 + 反汇编若干区间。

用法: python scripts/_tmp_q.py
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000

STRS = [
    0x1095f46c,   # B 0x10650730 成功路径 fmt
    0x1095f480,   # B 0x10650730 失败路径 fmt
    0x1095f4c4,   # B singleipconnect 0x650b85 的 fmt
    0x1095f4d4,   # B singleipconnect 0x650b5f 的 fmt
    0x1095f4a0,   # B singleipconnect 0x650d8a 的 fmt
    0x1095f4c0,
    0x107ac794,   # 'libcurl/7.65.1' ?
    0x1095dd7c,   # 'libcurl/7.63.0' ?
]

DIS = [
    (0x10425150, 0x104251f0),   # A: 对偶 B 的 0x10650790（tcpnagle 之后调用）
    (0x1044cfc0, 0x1044d030),   # A: inet_ntop IPv4 核心
    (0x10667d80, 0x10667e30),   # B: inet_ntop IPv6 核心
]

img = Image()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

for va in STRS:
    s = img.cstr(va - IMAGE_BASE, 96)
    print('0x%08x  %r' % (va, s))
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

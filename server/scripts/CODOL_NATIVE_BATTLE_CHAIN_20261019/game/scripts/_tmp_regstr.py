"""临时（只读）：给若干 .text 区间列**指令边界合法**的 .rdata 字符串引用。

用途 = 归属判据。importmap 已给出全 DLL 的 socket/connect/bind/... 调用点；
凡不在已识别 libcurl 区间内的调用点，其宿主区间必须逐一归属，
以回答"是否存在游戏自己的网络栈"。

用法: python scripts/_tmp_regstr.py
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000
RD_HI = IMAGE_BASE + 0x009af000
RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')

# 全部来自 importmap.py 的网络调用点宿主的**簇区间**（RVA 低形式）
REGIONS = [
    ('0x235xxx 事件驱动客户端', 0x235c00, 0x236200),
    ('0x2b3xxx getaddrinfo/nameinfo 库', 0x2b3700, 0x2b3f80),
    ('0x2d9xxx socket/connect/send/recv', 0x2d9400, 0x2d9a00),
    ('0x4438xx WSAIoctl/setsockopt', 0x443800, 0x443a00),
    ('0x4450xx recv', 0x444f00, 0x445200),
    ('0x51caxx send/recv/shutdown', 0x51c900, 0x51cd00),
    ('0x6160xx WSAStartup', 0x615f00, 0x616200),
    ('0x6410xx socket/select', 0x641000, 0x641c00),
    ('0x64bxxx recv/send', 0x64bd00, 0x64c600),
    ('0x64fdxx WSAIoctl/setsockopt', 0x64fd00, 0x64ff00),
    ('0x6621xx recv', 0x662100, 0x662300),
    ('0x6728xx WSAStartup/send/bind', 0x672800, 0x672c00),
    ('0x6735xx send', 0x673500, 0x673700),
    ('0x6744xx accept/listen/bind', 0x674400, 0x674e00),
    ('0x682exx WSAIoctl/setsockopt', 0x682e00, 0x683000),
    ('0x686cxx ioctlsocket', 0x686c00, 0x686e00),
    ('0x6a60xx gethostname', 0x6a6000, 0x6a6200),
    ('0x41eexx A-libcurl transfer recv', 0x41ee00, 0x41f000),
    ('0x41f3xx A-libcurl recv/send', 0x41f300, 0x41f800),
    ('0x4200xx select/WSAStartup', 0x41ff00, 0x421000),
    ('0x4247xx WSAIoctl/setsockopt', 0x424700, 0x425100),
]

SPAN_MAX = 0x1000


def main():
    img = Image()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'regstr.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    for (label, lo_rva, hi_rva) in REGIONS:
        lo = IMAGE_BASE + lo_rva
        hi = IMAGE_BASE + hi_rva
        if hi - lo > SPAN_MAX:
            hi = lo + SPAN_MAX
        buf = img.read(lo_rva, hi - lo)   # pe.Image.read 收 RVA
        if not buf:
            P('### 0x%08x  %s  -> 读取失败' % (lo, label))
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
                        s = img.cstr(v - IMAGE_BASE, 64)
                        if s and s.strip():
                            seen.append((addr, v, s))
            if got == 0:
                i += 1
            else:
                i += got
        P('### %s   (0x%08x-0x%08x, %d 条串引用)'
          % (label, lo, hi, len(seen)))
        prev = None
        shown = 0
        for (a, v, s) in seen:
            if s == prev:
                continue
            prev = s
            P('    @0x%08x  0x%08x  %r' % (a, v, s))
            shown += 1
            if shown >= 40:
                P('    ... (截断)')
                break
        P()
    out.close()
    print('-> scripts/_out/regstr.txt')


if __name__ == '__main__':
    main()

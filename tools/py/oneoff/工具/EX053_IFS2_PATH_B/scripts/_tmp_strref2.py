"""临时（只读）：**指令边界感知**的 .rdata 引用扫描。

与 _tmp_strref.py 的区别：旧脚本按原始字节找 4 字节模式，会把
`8b 91 a8 01 00 00 / 89 10` 这类指令流里偶然出现的 `00 00 89 10`
误判成「引用 0x10890000」。本脚本用 capstone 线性解码（遇非法字节跳 1 再同步），
只统计**真指令操作数里**落在 .rdata 范围的立即数。

用法:
    python scripts/_tmp_strref2.py            # 全窗口气球普查
    python scripts/_tmp_strref2.py <VA> ...   # 附加：指定目标的引用点验证
"""
import sys, os, re, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000          # .rdata VA 起
RD_HI = IMAGE_BASE + 0x009af000          # .rdata VA 止

RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')

WINDOWS = [
    (IMAGE_BASE + 0x00400000, IMAGE_BASE + 0x00470000, 'A 窗 0x0040_0000-0x0047_0000'),
    (IMAGE_BASE + 0x00630000, IMAGE_BASE + 0x006a0000, 'B 窗 0x0063_0000-0x006a_0000'),
]


def decode_refs(img):
    """线性解码 .text，返回 [(ins_addr_va, [target_va,...])]。"""
    sec = [s for s in img.sections if s['name'] == '.text'][0]
    buf = img.data[sec['raw']:sec['raw'] + sec['rawsize']]
    base = sec['va']
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    out = []
    n = len(buf)
    i = 0
    while i < n:
        got = 0
        for (addr, size, mn, ops) in md.disasm_lite(buf[i:], IMAGE_BASE + base + i):
            got = (addr - (IMAGE_BASE + base + i)) + size
            tgts = []
            for m in RE_IMM.finditer(ops):
                v = int(m.group(1), 16)
                if RD_LO <= v < RD_HI:
                    tgts.append(v)
            if tgts:
                out.append((addr, tgts))
        if got == 0:
            i += 1
        else:
            i += got
    return out


def main():
    img = Image()
    verify = [int(a, 16) for a in sys.argv[1:]]
    print('线性解码 .text ...')
    refs = decode_refs(img)
    print('含 .rdata 立即数的指令: %d 条' % len(refs))
    print()

    for (lo, hi, lab) in WINDOWS:
        sub = [(a, t) for (a, t) in refs if lo <= a < hi]
        allt = set()
        for (a, t) in sub:
            allt.update(t)
        print('=== %s : %d 条指令 / %d 个去重字符串地址 ===' % (lab, len(sub), len(allt)))
        print()

    # 每个窗口的字符串样本
    for (lo, hi, lab) in WINDOWS:
        sub = [(a, t) for (a, t) in refs if lo <= a < hi]
        cnt = collections.Counter()
        for (a, t) in sub:
            for v in t:
                cnt[v] += 1
        print('=== %s : 引用最多的字符串地址 top 40 ===' % lab)
        for v, c in cnt.most_common(40):
            s = img.cstr(v - IMAGE_BASE, 60)
            print('   x%-4d 0x%08x  %r' % (c, v, s))
        print()

    if verify:
        print('=== 指定目标 VA 的引用点验证 ===')
        for v in verify:
            hits = [(a, t) for (a, t) in refs if v in t]
            s = img.cstr(v - IMAGE_BASE, 60)
            print('  VA 0x%08x %r -> %d 处' % (v, s, len(hits)))
            for (a, t) in hits:
                print('       @0x%08x' % a)
        print()


if __name__ == '__main__':
    main()

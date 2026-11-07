"""临时（只读）：.rdata 字符串池分簇 + 每簇的 .text 引用者区间。

连接器按库为单位连续排布，所以 .rdata 的簇与 .text 的簇**同序**。
每个 .rdata 桶报告：被引用的去重串数、top 串、以及引用它的 .text 指令地址区间。
这样可以把 .rdata 簇与 .text 簇一一配对，判明每个 .text 区段属于哪个库。

用法: python scripts/_tmp_rdata_map.py
输出: scripts/_out/rdata_map.txt
"""
import sys, os, re, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000
RD_HI = IMAGE_BASE + 0x009af000
RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')


def main():
    img = Image()
    sec = [x for x in img.sections if x['name'] == '.text'][0]
    buf = img.data[sec['raw']:sec['raw'] + sec['rawsize']]
    base = sec['va']
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    refs = []      # (string_va, ins_va)
    i = 0
    n = len(buf)
    while i < n:
        got = 0
        for (addr, size, mn, ops) in md.disasm_lite(buf[i:], IMAGE_BASE + base + i):
            got = (addr - (IMAGE_BASE + base + i)) + size
            for m in RE_IMM.finditer(ops):
                v = int(m.group(1), 16)
                if RD_LO <= v < RD_HI:
                    refs.append((v, addr))
        if got == 0:
            i += 1
        else:
            i += got

    buckets = collections.defaultdict(list)
    for (sva, ia) in refs:
        buckets[(sva - IMAGE_BASE) // 0x10000].append((sva, ia))

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'rdata_map.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    P('.rdata 桶    被引串  引用指令数  引用者 .text 区间(5%%-95%%)   top 串')
    for b in sorted(buckets):
        lst = buckets[b]
        cnt = collections.Counter(v for (v, _) in lst)
        ias = sorted(a for (_, a) in lst)
        lo = ias[int(len(ias) * 0.05)]
        hi = ias[min(len(ias) - 1, int(len(ias) * 0.95))]
        strs = []
        for v, c in cnt.most_common(5):
            try:
                s = img.cstr(v - IMAGE_BASE, 46)
            except Exception:
                s = None
            strs.append('x%d %r' % (c, s))
        P('0x%06x  %6d  %8d   0x%08x-0x%08x   %s'
          % (b * 0x10000, len(cnt), len(lst), lo, hi, ' | '.join(strs)))
    out.close()
    print('-> scripts/_out/rdata_map.txt (%d 桶, %d 条引用)' % (len(buckets), len(refs)))


if __name__ == '__main__':
    main()

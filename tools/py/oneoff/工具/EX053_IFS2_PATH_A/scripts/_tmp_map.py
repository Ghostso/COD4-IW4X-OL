"""临时（只读）：按 64KB 桶给 .text 做「第三方库归属图」。

判据 = 该桶内**指令边界合法**的 .rdata 立即数引用所指字符串。
用法: python scripts/_tmp_map.py
输出: scripts/_out/texmap.txt
"""
import sys, os, re, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
RD_LO = IMAGE_BASE + 0x00743000
RD_HI = IMAGE_BASE + 0x009af000
RE_IMM = re.compile(r'0x([0-9a-f]{6,8})\b')

TAGS = [
    ('curl', re.compile(r'libcurl|curl_|CURLOPT|"curl')),      # 占位，实际用子串
]


def tag_of(s):
    if s is None:
        return '?'
    for k in ('libcurl/', 'ssl\\ssl', '.\\ssl\\', 'crypto\\', '.\\crypto\\',
              'OpenSSL', 'imgproc', 'cvHough', 'opencv'):
        if k in s:
            return k
    return None


def main():
    img = Image()
    sec = [x for x in img.sections if x['name'] == '.text'][0]
    buf = img.data[sec['raw']:sec['raw'] + sec['rawsize']]
    base = sec['va']
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    buckets = collections.defaultdict(list)   # bkt -> [(ins_va, saddr_va)]
    i = 0
    n = len(buf)
    while i < n:
        got = 0
        for (addr, size, mn, ops) in md.disasm_lite(buf[i:], IMAGE_BASE + base + i):
            got = (addr - (IMAGE_BASE + base + i)) + size
            for m in RE_IMM.finditer(ops):
                v = int(m.group(1), 16)
                if RD_LO <= v < RD_HI:
                    buckets[(addr - IMAGE_BASE) // 0x10000].append((addr, v))
        if got == 0:
            i += 1
        else:
            i += got

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'texmap.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    P('rva_bucket  insn_refs  uniq_str  top_strs')
    for b in sorted(buckets):
        lst = buckets[b]
        cnt = collections.Counter(v for (_, v) in lst)
        strs = []
        for v, c in cnt.most_common(6):
            try:
                s = img.cstr(v - IMAGE_BASE, 48)
            except Exception:
                s = None
            strs.append('x%d %r' % (c, s))
        P('0x%06x  %5d  %5d  %s' % (b * 0x10000, len(lst), len(cnt),
                                    ' | '.join(strs)))
    out.close()
    print('-> scripts/_out/texmap.txt  (%d 桶, %d 条引用)'
          % (len(buckets), sum(len(v) for v in buckets.values())))


if __name__ == '__main__':
    main()

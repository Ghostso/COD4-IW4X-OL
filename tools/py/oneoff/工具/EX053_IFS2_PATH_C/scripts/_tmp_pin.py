"""临时（只读）：钉死 curl 版本串与 _SHAREDMEMEMORY 的归属。

1. 全文件定位 b'_SHAREDMEMEMORY' / b'libcurl/7.6' 的出现位置（RVA）并打印上下文。
2. 对给定 RVA 目标，扫描 .text 全节里的 imm32 == IMAGE_BASE+RVA，列出引用点。
3. 反汇编给定地址附近的指令。
"""
import sys, os, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X

IMAGE_BASE = 0x10000000


def raw2rva(img, foff):
    for s in img.sections:
        if s['raw'] <= foff < s['raw'] + s['rawsize']:
            return s['va'] + (foff - s['raw'])
    return None


def ctx(img, foff, before=48, after=110):
    a = max(0, foff - before)
    b = foff + after
    return img.data[a:b]


def main():
    img = Image()
    print('sections:')
    for s in img.sections:
        print('   %-8s va=0x%08x vsize=0x%x raw=0x%08x rawsize=0x%x'
              % (s['name'], s['va'], s['vsize'], s['raw'], s['rawsize']))
    print()

    data = img.data
    targets = {}
    for pat in (b'_SHAREDMEMEMORY', b'libcurl/7.6', b'TCLS'):
        print('=== pattern %r ===' % pat)
        start = 0
        n = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            n += 1
            rva = raw2rva(img, i)
            print('  file 0x%08x  rva %s' % (i, ('0x%08x' % rva) if rva else '??'))
            print('     ctx: %r' % (ctx(img, i),))
            if rva is not None:
                targets.setdefault(rva, pat.decode())
            start = i + 1
            if n >= 25:
                print('  ... (>25)')
                break
        print()

    # ---- 扫描 .text 里指向这些 RVA 的 imm32 ----
    sec = img.sections[0]
    buf = data[sec['raw']:sec['raw'] + sec['rawsize']]
    print('=== imm32 xref 扫描 (.text va=0x%08x size=0x%x) ===' % (sec['va'], sec['rawsize']))
    for rva, lab in sorted(targets.items()):
        va = IMAGE_BASE + rva
        b = struct.pack('<I', va)
        hits = []
        start = 0
        while True:
            i = buf.find(b, start)
            if i < 0:
                break
            hits.append(sec['va'] + i)
            start = i + 1
        print('  VA 0x%08x  "%s"  -> %d 处: %s'
              % (va, lab[:40], len(hits),
                 ', '.join('0x%08x' % (IMAGE_BASE + h) for h in hits[:20])))
    print()

    # ---- 反汇编两处 _SHAREDMEMEMORY 引用点 ----
    print('=== 反汇编 _SHAREDMEMEMORY 引用点附近 ===')
    for va in (0x1043093a, 0x10642cf5):
        rva = va - IMAGE_BASE
        print('-- @0x%08x --' % va)
        try:
            for ins in X.dis(img, rva - 0x30, 0x60):
                print('   %08x  %-20s %s %s'
                      % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        except Exception as e:
            print('   [fail %r]' % e)
        print()


if __name__ == '__main__':
    main()

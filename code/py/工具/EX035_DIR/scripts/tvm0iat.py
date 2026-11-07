"""扫描指定节内「指令边界已验证」的 call [abs32]（FF 15），映射到 .idata2 槽 -> dll!api。

做两件事，并刻意区分：
  A. 原始字节扫描：数 FF 15 出现的字节序列个数（**不是**证据，可能是别的指令的操作数）。
  B. 线性扫描反汇编：只有 capstone 真的从某个边界解出 `call dword ptr [imm32]`
     才计入。这才是「指令边界验证过」的调用点。
  A - B 的差额 = 落在指令内部、不构成真实调用的伪 FF 15。

用法:
    python scripts/tvm0iat.py <secname> [secname2 ...]
"""
import sys, os, struct, collections, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import importmap
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
IAT_LO, IAT_HI = 0xb02000, 0xb07000


def raw_ff15_count(img, sec):
    start, end = sec['raw'], sec['raw'] + sec['rawsize']
    n = 0
    i = img.data.find(b'\xff\x15', start, end)
    while i >= 0:
        n += 1
        i = img.data.find(b'\xff\x15', i + 1, end)
    return n


def sweep(img, sec, slots, md, chunk=1 << 16):
    """线性扫描反汇编 + 重同步。

    capstone 一遇非法字节就停，必须靠「跳 1 字节重试」继续。块之间用
    「上一条成功解码指令的结束偏移」续接，避免在块边界丢掉跨块指令。
    """
    start = sec['raw']
    buf = img.data[start:start + sec['rawsize']]
    base = sec['va']
    n = len(buf)
    calls = []           # (call_va, slot_va, api)
    off_iat = 0          # FF15 指向 .idata2 区间但不在已知槽里（越界/空洞）
    off_out = 0          # FF15 指向模块外 / 非常量
    total_insn = 0
    covered = 0          # 被成功解码指令覆盖的字节数
    bad = 0              # 重同步丢弃的字节数
    t0 = time.time()

    pos = 0
    while pos < n:
        end = min(pos + chunk, n)
        blob = buf[pos:end]
        i = 0
        last_good = 0
        while i < len(blob):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(blob[i:], base + pos + i):
                total_insn += 1
                covered += size
                got = (addr - (base + pos + i)) + size
                if mn == 'call' and ops.startswith('dword ptr [0x'):
                    v = int(ops[13:-1], 16)
                    if v >= IMAGE_BASE:
                        r = v - IMAGE_BASE
                        if r in slots:
                            calls.append((addr, r, slots[r]))
                        elif IAT_LO <= r < IAT_HI:
                            off_iat += 1
                        else:
                            off_out += 1
                    else:
                        off_out += 1
            if got == 0:
                i += 1
                bad += 1
            else:
                i += got
                last_good = i
        # 下一块从「最后一条成功指令的末尾」续接；整块无解码则整块跳过
        pos += last_good if last_good else chunk

    return calls, dict(total_insn=total_insn, off_iat=off_iat, off_out=off_out,
                       covered=covered, bad=bad, secs=time.time() - t0)


def main():
    names = sys.argv[1:] or ['.tvm0']
    img = Image()
    slots = importmap.build(img)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    bysec = {}
    for nm in names:
        sec = [s for s in img.sections if s['name'] == nm]
        if not sec:
            print('!! 无此节: %s' % nm)
            continue
        sec = sec[0]
        raw = raw_ff15_count(img, sec)
        calls, st = sweep(img, sec, slots, md)
        bysec[nm] = calls
        print('=' * 72)
        print('节 %-8s  RVA 0x%08x  vsize 0x%x  rawsize 0x%x' %
              (nm, sec['va'], sec['vsize'], sec['rawsize']))
        print('  FF15 原始字节序列      : %d   (非证据)' % raw)
        print('  线性解码指令总数        : %d   (%.1fs)' % (st['total_insn'], st['secs']))
        print('  解码覆盖字节 / 节大小   : %d / %d = %.1f%%   重同步丢弃 %d 字节'
              % (st['covered'], sec['rawsize'],
                 100.0 * st['covered'] / max(1, sec['rawsize']), st['bad']))
        print('  边界已验证 call[abs32]  : %d   <= 真实调用点' % len(calls))
        print('  指向 .idata2 但非已知槽 : %d' % st['off_iat'])
        print('  指向模块外 / 非常量     : %d' % st['off_out'])
        print('  伪 FF15（落在指令内部） : %d' % (raw - len(calls)))
        c = collections.Counter(a.split('!')[0].rstrip('?') for _, _, a in calls)
        print('  --- 按 DLL ---')
        for d, n in c.most_common():
            print('      %-16s %5d' % (d, n))

    allc = [c for v in bysec.values() for c in v]
    print()
    print('=' * 72)
    print('## 全部真调用点按 dll!api 汇总')
    c = collections.Counter(a for _, _, a in allc)
    for a, n in c.most_common():
        print('   %-46s %4d' % (a, n))

    print()
    print('## 调用点明细（RVA, 槽, api）按 RVA 升序，最多 400 条')
    for va, sr, api in sorted(set(allc))[:400]:
        print('   0x%08x  slot 0x%06x  %s' % (va, sr, api))


if __name__ == '__main__':
    main()

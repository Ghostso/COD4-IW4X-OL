"""双向跨节边统计 + .text 基线（用于对照 .tvm0 的间接转移密度）。

用法: python scripts/xtab.py
"""
import sys, os, collections, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

JCC = set("""je jne jz jnz ja jae jb jbe jg jge jl jle js jns jo jno jp jnp
 jc jnc jecxz loop loopd loope loopne""".split())

def stats(img, sec, md, want_edges=True):
    base, rawsize = sec['va'], sec['rawsize']
    buf = img.data[sec['raw']:sec['raw'] + rawsize]
    n = len(buf); CH = 1 << 16; pos = 0
    h = dict(insn=0, covered=0, bad=0, jmp_reg=0, jmp_mem=0, call_reg=0,
             call_mem=0, push_ret=0, real_ret=0, other_ind=0)
    edges = collections.Counter()
    tgts = collections.Counter()     # 跨 out-of-section 直接目标直方图
    prev_push = None
    while pos < n:
        end = min(pos + CH, n); blob = buf[pos:end]; i = 0; last_good = 0
        while i < len(blob):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(blob[i:], base + pos + i):
                h['insn'] += 1; h['covered'] += size
                got = (addr - (base + pos + i)) + size
                if mn == 'call' and ops.startswith('dword ptr ['):
                    h['call_mem'] += 1
                elif mn == 'call' and not ops.startswith('0x'):
                    h['call_reg'] += 1
                elif mn in ('call', 'jmp', 'ljmp') and ':' not in ops and ops.startswith('0x'):
                    t = int(ops, 16)
                    if want_edges:
                        src = '.tvm0' if base == 0x19dd000 else '.text'
                        edges[(src, which(img, t), mn)] += 1
                        if src == '.tvm0':
                            if 0x1000 <= t < 0x1000 + 0x742000:
                                tgts[t] += 1
                        else:
                            if 0x19dd000 <= t < 0x19dd000 + 0x1f5e000:
                                tgts[t] += 1
                    if mn in ('jmp', 'ljmp'):
                        if '[' in ops: h['jmp_mem'] += 1
                elif mn in ('jmp', 'ljmp') and not ops.startswith('0x'):
                    if '[' in ops: h['jmp_mem'] += 1
                    else: h['jmp_reg'] += 1
                elif mn in JCC and ops.startswith('0x') and ':' not in ops:
                    t = int(ops, 16)
                    if want_edges:
                        edges[(which(img, addr), which(img, t), 'jcc')] += 1
                elif mn in ('ret', 'retn', 'retf'):
                    if not ops and prev_push is not None: h['push_ret'] += 1
                    else: h['real_ret'] += 1
                prev_push = ops if mn == 'push' else None
            if got == 0: i += 1; h['bad'] += 1; prev_push = None
            else: i += got; last_good = i
        pos += last_good if last_good else CH
    return h, edges, tgts

_SECS = None
def which(img, x):
    return _SECS.which(x) if _SECS else '?'

class _W:
    def __init__(self, img):
        self.s = [(s['name'], s['va'], s['va'] + s['vsize']) for s in img.sections]
    def which(self, x):
        for n, a, b in self.s:
            if a <= x < b: return n
        return 'OUT'

def main():
    global _SECS
    img = Image(); _SECS = _W(img)
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    allt = collections.Counter()
    for nm in ('.tvm0', '.text'):
        sec = [s for s in img.sections if s['name'] == nm][0]
        t0 = time.time()
        h, edges, tgts = stats(img, sec, md)
        tot_ind = h['jmp_reg'] + h['jmp_mem'] + h['call_reg'] + h['call_mem'] + h['push_ret']
        print('=' * 72)
        print('节 %s  rawsize 0x%x  指令 %d  覆盖 %.1f%%  用时 %.1fs'
              % (nm, sec['rawsize'], h['insn'], 100.0*h['covered']/sec['rawsize'], time.time()-t0))
        print('   jmp reg %d   jmp mem %d   call reg %d   call mem %d   push;ret %d   ret %d'
              % (h['jmp_reg'], h['jmp_mem'], h['call_reg'], h['call_mem'], h['push_ret'], h['real_ret']))
        print('   间接转移合计 %d   占指令 %.3f%%' % (tot_ind, 100.0*tot_ind/h['insn']))
        print('   --- 跨节边 ---')
        for (s, d, k), c in edges.most_common():
            print('     %-8s -> %-8s %-5s %8d' % (s, d, k, c))
        if nm == '.tvm0':
            print('   --- .tvm0 -> .text 目标直方图 top40 ---')
            for t, c in tgts.most_common(40):
                print('     0x%08x  %5d' % (t, c))
            print('   目标种类 %d   合计 %d' % (len(tgts), sum(tgts.values())))
        else:
            print('   --- .text -> .tvm0 目标直方图 top40 ---')
            for t, c in tgts.most_common(40):
                print('     0x%08x  %5d' % (t, c))
            print('   目标种类 %d   合计 %d' % (len(tgts), sum(tgts.values())))

if __name__ == '__main__':
    main()

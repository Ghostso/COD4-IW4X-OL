"""对 .tvm0 做全节线性扫描，统计「VM/分发器」特征与跨节乒乓边。

刻意区分「原始字节模式」与「指令边界已验证的解码结果」。
用法: python scripts/tvm0vm.py
"""
import sys, os, struct, collections, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import importmap
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
JCC = set("""je jne jz jnz ja jae jb jbe jg jge jl jle js jns jo jno jp jnp
 jc jnc jecxz loop loopd loope loopne""".split())

def secs_of(img):
    return [(s['name'], s['va'], s['va'] + s['vsize']) for s in img.sections]

def which(secs, x):
    for n, a, b in secs:
        if a <= x < b:
            return n
    return 'OUT'

def main():
    img = Image()
    slots = importmap.build(img)
    secs = secs_of(img)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    tvm = [s for s in img.sections if s['name'] == '.tvm0'][0]
    start, rawsize, base = tvm['raw'], tvm['rawsize'], tvm['va']
    buf = img.data[start:start + rawsize]
    n = len(buf)

    CH = 1 << 16
    pos = 0
    h = dict(
        insn=0, covered=0, bad=0,
        jmp_reg=0, jmp_mem=0, call_reg=0, call_mem=0,
        push_ret=0, real_ret=0,
        iat_calls=collections.Counter(),
        iat_sites=collections.defaultdict(list),
        edges=collections.Counter(),
        key_add=collections.Counter(),
        rol_count=collections.Counter(),
    )
    prev_push = None
    t0 = time.time()

    while pos < n:
        end = min(pos + CH, n)
        blob = buf[pos:end]
        i = 0
        last_good = 0
        while i < len(blob):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(blob[i:], base + pos + i):
                h['insn'] += 1; h['covered'] += size
                got = (addr - (base + pos + i)) + size
                if mn == 'call' and ops.startswith('dword ptr [0x'):
                    h['call_mem'] += 1
                    v = int(ops[13:-1], 16)
                    if v >= IMAGE_BASE:
                        r = v - IMAGE_BASE
                        if r in slots:
                            h['iat_calls'][slots[r]] += 1
                            h['iat_sites'][slots[r]].append(addr)
                elif mn == 'call' and not ops.startswith('0x'):
                    h['call_reg'] += 1
                elif mn == 'call':
                    if ':' in ops:
                        h['edges'][('.tvm0', 'FAR', 'call')] += 1
                    else:
                        h['edges'][('.tvm0', which(secs, int(ops, 16)), 'call')] += 1
                elif mn in ('jmp', 'ljmp') and not ops.startswith('0x'):
                    if '[' in ops: h['jmp_mem'] += 1
                    else: h['jmp_reg'] += 1
                elif mn in ('jmp', 'ljmp'):
                    if ':' in ops:
                        h['edges'][('.tvm0', 'FAR', 'jmp')] += 1
                    else:
                        h['edges'][('.tvm0', which(secs, int(ops, 16)), 'jmp')] += 1
                elif mn in JCC and ops.startswith('0x') and ':' not in ops:
                    h['edges'][('.tvm0', which(secs, int(ops, 16)), 'jcc')] += 1
                elif mn in ('ret', 'retn', 'retf'):
                    if not ops and prev_push is not None:
                        h['push_ret'] += 1
                    else:
                        h['real_ret'] += 1

                prev_push = ops if mn == 'push' else None
                if mn in ('add', 'sub', 'xor'):
                    toks = ops.split(', ')
                    if len(toks) == 2 and toks[1].startswith('0x') and len(toks[1]) >= 10:
                        h['key_add'][(mn, toks[1])] += 1
                if mn in ('rol', 'ror'):
                    h['rol_count'][ops] += 1
            if got == 0:
                i += 1; h['bad'] += 1; prev_push = None
            else:
                i += got; last_good = i
        pos += last_good if last_good else CH

    print('=' * 72)
    print('.tvm0 线性扫描  rawsize 0x%x  解码指令 %d  覆盖 %d (%.1f%%)  重同步丢弃 %d  用时 %.1fs'
          % (rawsize, h['insn'], h['covered'], 100.0*h['covered']/rawsize, h['bad'], time.time()-t0))
    print()
    print('## 间接控制转移（边界已验证）')
    print('   jmp reg            %d' % h['jmp_reg'])
    print('   jmp [mem]          %d' % h['jmp_mem'])
    print('   call reg           %d' % h['call_reg'])
    print('   call [mem]         %d   <- 其中映射到 .idata2 槽 %d'
          % (h['call_mem'], sum(h['iat_calls'].values())))
    print('   push x; ret        %d   <- 手写间接跳转(模仿 jmp)' % h['push_ret'])
    print('   真 ret             %d' % h['real_ret'])
    print()
    print('## 跨节直接边 (.tvm0 -> ?)')
    for (s, d, k), c in h['edges'].most_common():
        print('   %-8s -> %-8s %-5s  %d' % (s, d, k, c))
    print()
    print('## 反复出现的 32 位常量（add/sub/xor reg,imm32）  top30')
    for (k, v), c in h['key_add'].most_common(30):
        print('   %-4s %-12s %6d' % (k, v, c))
    print()
    print('## rol/ror  top15')
    for v, c in h['rol_count'].most_common(15):
        print('   %-24s %6d' % (v, c))
    print()
    print('## .tvm0 内 call [.idata2] 按 API')
    for a, c in h['iat_calls'].most_common():
        print('   %-46s %4d' % (a, c))
    print()
    print('## .tvm0 内网络相关调用点')
    KEY = ('socket', 'connect', 'send', 'recv', 'bind', 'listen', 'accept',
           'select', 'closesocket', 'hton', 'ntoh', 'inet_', 'getaddrinfo',
           'getnameinfo', 'freeaddrinfo', 'setsockopt', 'getsockopt',
           'shutdown', 'WSA', 'gethost')
    for a in sorted(h['iat_sites']):
        if any(k in a for k in KEY):
            print('   %-40s %s' % (a, ', '.join('0x%08x' % p for p in h['iat_sites'][a])))
    print()
    print('## .tvm0 全部调用点明细按 API 分组（每 API 最多 40 条）')
    for a in sorted(h['iat_sites']):
        pts = h['iat_sites'][a]
        print('   %-46s %4d  %s' % (a, len(pts), ', '.join('0x%08x' % p for p in sorted(pts)[:40])))

if __name__ == '__main__':
    main()

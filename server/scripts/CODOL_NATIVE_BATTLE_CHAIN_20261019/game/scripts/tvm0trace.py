"""从 .tvm0 入口做递归下降控制流恢复（只读）。

统一地址空间：全程用 RVA（pe.read / X.dis 都吃 RVA）。
X.dis(img, rva, n) 内部按 rva 当 capstone address 标注，因此打印出的
分支目标数字就是 RVA，不是 VA —— 判节必须用 section_of(rva)。

用法:
    python scripts/tvm0trace.py <hexrva> [max_insns]
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

JCC = set("""je jne jz jnz ja jae jb jbe jg jge jl jle js jns jo jno jp jnp
 jc jnc jecxz loop loopd loope loopne""".split())

INDIRECT = {'jmp', 'call'}


def decode_one(md, img, rva):
    b = img.read(rva, 15)
    if not b:
        return None
    for ins in md.disasm(b, rva):
        return ins
    return None


def run(img, md, entry, max_insn=40000):
    secs = [(s['name'], s['va'], s['va'] + s['vsize']) for s in img.sections]
    lo = min(a for _, a, _ in secs)
    hi = max(b for _, _, b in secs)

    def which(x):
        for n, a, b in secs:
            if a <= x < b:
                return n
        return None

    todo = collections.deque([entry])
    seen_starts = set()
    insns = {}            # rva -> ins  (first decode wins)
    edges = []            # (from_rva, kind, target_rva_or_None)
    indirect = []         # (rva, ins, section, note)
    rets = []
    out_of_range = []
    count = 0
    order = []

    while todo and count < max_insn:
        start = todo.popleft()
        if start in seen_starts:
            continue
        seen_starts.add(start)
        rva = start
        prev = None
        # decode a basic block
        while count < max_insn:
            if rva in insns:
                break                      # 已解码过 -> 与既有块合流
            if not (lo <= rva < hi):
                out_of_range.append((start, rva, which(rva)))
                break
            ins = decode_one(md, img, rva)
            if ins is None:
                break
            insns[rva] = ins
            order.append(rva)
            count += 1
            mn = ins.mnemonic
            ops = ins.op_str

            if mn == 'ret' or mn == 'retn' or mn == 'retf':
                # push <reg|mem> ; ret  = 手写间接跳转（ret 当 jmp 用），
                # 不是函数返回。上一轮工具漏掉了这一类。
                if (not ops and prev is not None and prev.mnemonic == 'push'):
                    indirect.append((rva, ins, which(rva),
                                     'push %s ; ret  (手写间接跳转)'
                                     % prev.op_str))
                    edges.append((rva, 'ret-indirect', None))
                else:
                    rets.append((rva, ins))
                    edges.append((rva, 'ret', None))
                break

            if mn in INDIRECT:
                # call/jmp [mem] / call/jmp reg  -> 间接
                if not (ops.startswith('0x') and '[' not in ops):
                    indirect.append((rva, ins, which(rva), ''))
                    edges.append((rva, mn + '-indirect', None))
                    # call reg/[mem] 仍然会返回 -> 继续 fallthrough
                    if mn == 'call':
                        prev = ins
                        rva += ins.size
                        continue
                    break
                # 直接 rel32
                tgt = int(ops, 16)
                edges.append((rva, mn, tgt))
                if mn == 'call':
                    if lo <= tgt < hi:
                        todo.append(tgt)
                    else:
                        out_of_range.append((rva, tgt, which(tgt)))
                    prev = ins
                    rva += ins.size
                    continue
                # jmp
                if lo <= tgt < hi:
                    todo.append(tgt)
                else:
                    out_of_range.append((rva, tgt, which(tgt)))
                break

            if mn in JCC:
                if ops.startswith('0x'):
                    tgt = int(ops, 16)
                    edges.append((rva, mn, tgt))
                    if lo <= tgt < hi:
                        todo.append(tgt)
                    else:
                        out_of_range.append((rva, tgt, which(tgt)))
                prev = ins
                rva += ins.size
                continue

            prev = ins
            rva += ins.size

    return dict(insns=insns, edges=edges, indirect=indirect, rets=rets,
                out_of_range=out_of_range, order=order)


def main():
    entry = int(sys.argv[1], 16)
    max_insn = int(sys.argv[2]) if len(sys.argv) > 2 else 40000
    img = Image()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    r = run(img, md, entry, max_insn)

    secs = [(s['name'], s['va'], s['va'] + s['vsize']) for s in img.sections]

    def which(x):
        for n, a, b in secs:
            if a <= x < b:
                return n
        return None

    print("=" * 64)
    print("入口 RVA 0x%08x   解码指令数 %d   基本块起点 %d" %
          (entry, len(r['insns']), len(set(
              [entry] + [t for _, k, t in r['edges'] if t]))))
    print("=" * 64)

    print("\n## 前 60 条（入口顺序解码，遇 jmp/ret 即止）")
    n = 0
    for rva in r['order']:
        ins = r['insns'][rva]
        ex = ""
        if ins.op_str.startswith('0x') and (ins.mnemonic in JCC
                                            or ins.mnemonic in INDIRECT):
            t = int(ins.op_str, 16)
            ex = "   -> RVA 0x%08x 节=%s" % (t, which(t))
        print("   %08x  %-20s %s %s%s" % (rva, ins.bytes.hex(), ins.mnemonic,
                                          ins.op_str, ex))
        n += 1
        if n >= 60:
            break

    print("\n## 间接控制转移（边界验证过的真实指令）  共 %d" %
          len(r['indirect']))
    for rec in r['indirect']:
        rva, ins, sec = rec[0], rec[1], rec[2]
        note = rec[3] if len(rec) > 3 else ''
        print("   %08x  [%s]  %-18s %-20s %s" % (rva, sec, ins.bytes.hex(),
                                                 ins.mnemonic + ' ' + ins.op_str,
                                                 note))

    print("\n## 普通 ret（真函数返回）  共 %d" % len(r['rets']))
    for rva, ins in r['rets'][:40]:
        print("   %08x  %s %s" % (rva, ins.mnemonic, ins.op_str))

    print("\n## 越界 / 非模块内目标  共 %d" % len(r['out_of_range']))
    for a, b, s in r['out_of_range'][:60]:
        print("   来自 %08x -> 目标 %08x 节=%s" % (a, b, s))

    print("\n## 目标所在节统计")
    c = collections.Counter()
    for a, k, t in r['edges']:
        if t is None:
            c['<indirect/ret>'] += 1
        else:
            c[which(t) or 'OUT'] += 1
    for k, v in c.most_common():
        print("   %-14s %d" % (k, v))


if __name__ == '__main__':
    main()

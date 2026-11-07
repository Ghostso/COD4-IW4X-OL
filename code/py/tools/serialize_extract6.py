#!/usr/bin/env python3
"""位流读写脚本提取器 v6 —— 用递归下降遍历基本块。

v5 及以前全部用"线性扫到第一条 ret 就停"，这会在 MSVC 把冷块
（错误处理/罕见分支）放在第一条 ret **之后** 时漏掉整段。
0x626b30 (Join::deserialize) 就是这种情况：真末段在 0x626bfe。

v6 改法：
  1. 以函数入口为根，做递归下降（顺序流 + 跳转目标都入队）
  2. 指令按地址升序处理，保证 push/call 配对顺序正确
  3. 条件跳转的两个出口都跟；ret 不跟
  4. 不跟进"尾调用 jmp"目标（那是别的函数）

输出与 v5 相同（bits/data/var/call + 循环标记），但多了 tag 值。
用法:
  python -I tools/serialize_extract6.py 0x626b30
  python -I tools/serialize_extract6.py --all
  python -I tools/serialize_extract6.py --tags
"""
import re
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WB, WD = 0xB77B10, 0xB777C0       # writeBits / writeData
RB, RD = 0xB774E0, 0xB772E0       # readBitsExpect / readData
MAXDEPTH = 5
MAXINS = 4000

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.detail = True


def decode_at(b, va):
    o = va - BASE
    if not (0 <= o < len(b) - 16):
        return None
    for ins in _md.disasm(b[o:o + 16], va):
        return ins
    return None


def func_insns(b, va):
    """递归下降，返回按地址排序的指令列表。"""
    out = {}
    work = [va]
    seen = set()
    n = 0
    while work and n < MAXINS:
        a = work.pop()
        if a in seen:
            continue
        seen.add(a)
        while n < MAXINS:
            ins = decode_at(b, a)
            if ins is None:
                break
            n += 1
            out[a] = ins
            m = ins.mnemonic
            if m.startswith("ret") or m == "int3":
                break
            # 条件/无条件跳转
            if m.startswith("j") and ins.operands and \
                    ins.operands[0].type == X.X86_OP_IMM:
                t = ins.operands[0].imm
                if m == "jmp":
                    # 尾调用（跨函数）不跟；函数内向前跳继续顺序处理由 work 覆盖
                    if va <= t < va + 0x3000:
                        work.append(t)
                    break
                if va <= t < va + 0x3000:
                    work.append(t)
            a += ins.size
        # 顺序流继续由内层 while 承担
    return [out[k] for k in sorted(out)]


_wc = {}


def is_writer(b, va, want, depth=0):
    key = (va, want)
    if key in _wc:
        return _wc[key]
    _wc[key] = False
    ok = False
    for ins in func_insns(b, va):
        if ins.mnemonic == "call" and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t == want:
                ok = True
                break
            if depth < 1 and is_writer(b, t, want, depth + 1):
                ok = True
                break
    _wc[key] = ok
    return ok


def width_of(pend):
    for p in reversed(pend):
        if p[0] == "imm":
            return p[1]
    return None


def analyze(b, va, tagcall, datacall, depth=0, stack=(), loops_ok=True):
    """返回 (seq, loops_found)"""
    empty = ([], 0)
    if va in stack or depth > MAXDEPTH:
        return empty
    stack = stack + (va,)
    ins_list = func_insns(b, va)
    if not ins_list:
        return empty

    # 后向跳转 = 循环
    addrs = sorted(out_a for out_a in (i.address for i in ins_list))
    ranges = []
    for ins in ins_list:
        if ins.mnemonic.startswith("j") and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t <= ins.address and va <= t:
                ranges.append((t, ins.address))

    def in_loop(a):
        return any(lo <= a <= hi for lo, hi in ranges)

    seq = []
    pend = []
    for ins in ins_list:
        m, ops = ins.mnemonic, ins.operands
        lp = in_loop(ins.address)
        if m == "push":
            if ops[0].type == X.X86_OP_IMM:
                pend.append(("imm", ops[0].imm))
            elif ops[0].type == X.X86_OP_MEM:
                pend.append(("mem",))
            else:
                pend.append(("reg",))
            pend = pend[-8:]
            continue
        if m == "call" and ops and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == tagcall:
                v = pend[-1][1] if pend and pend[-1][0] == "imm" else None
                seq.append((lp, "tag", 5, ins.address, v))
            elif t == datacall:
                w = width_of(pend)
                seq.append((lp, "data", w, ins.address, None))
            elif t in (WB, WD, RB, RD, 0xC427F0):
                pass
            elif is_writer(b, t, tagcall):
                sub, sl = analyze(b, t, tagcall, datacall, depth + 1, stack)
                if sub:
                    seq.append((lp, "call " + hex(t), None, ins.address, None))
                    seq.extend([(lp,) + tuple(s[1:]) for s in sub])
            pend = []
            continue
    return seq, len({r[0] for r in ranges})


def report(va, seq, loops):
    print("===== %#010x =====" % va)
    pre = loop = 0
    for lp, kind, w, at, tagv in seq:
        print("%s %-14s %-5s tag=%-5s @%#x" % (
            "  L" if lp else "   ", kind,
            ("%d" % w) if w is not None else "VAR",
            ("0x%02x" % tagv) if tagv is not None else "-", at))
        if w:
            if lp:
                loop += w
            else:
                pre += w
    print("-- 循环外 %d 位 = %.2f 字节" % (pre, pre / 8.0))
    if loops:
        print("-- 循环体 %d 位 = %.2f 字节 × N" % (loop, loop / 8.0))
    print()


def rows_from_vtable():
    import subprocess
    out = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    rows = []
    for line in out.splitlines():
        mm = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                      r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if mm:
            rows.append((mm.group(1), mm.group(4), mm.group(5)))
    return rows


def main():
    b = open(DUMP, "rb").read()
    if "--tags" in sys.argv or "--all" in sys.argv:
        want_tags = "--tags" in sys.argv
        seen = set()
        for name, sva, dva in rows_from_vtable():
            for label, f, tagc, datc in (("ser", sva, WB, WD),
                                         ("der", dva, RB, RD)):
                iv = int(f, 16)
                if (iv, tagc) in seen:
                    continue
                seen.add((iv, tagc))
                seq, loops = analyze(b, iv, tagc, datc)
                tags = [("L" if lp else "") + "%02x" % v
                        for lp, k, w, a, v in seq if k == "tag"]
                if want_tags:
                    print("%-46s %s %s" % (name, label, " ".join(tags)))
                else:
                    pre = sum(w for lp, k, w, a, v in seq if w and not lp)
                    lp_ = sum(w for lp, k, w, a, v in seq if w and lp)
                    print("%-46s %s pre=%-5d loop=%-5d x%d" % (
                        name, label, pre, lp_, loops))
        return
    va = int(sys.argv[1], 0)
    is_read = "--read" in sys.argv
    seq, loops = analyze(b, va,
                         RB if is_read else WB,
                         RD if is_read else WD)
    report(va, seq, loops)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""位流提取器 v4 —— 三个旧缺陷全部修掉：

  D1（v1/v2）不跟进子函数      → 跟进，且按 ret 严格界定函数边界
  D2（v2）"指针是寄存器 ⇒ 变长" → 只看位宽是否为立即数
  D3（v2/v3）反汇编窗口越过 ret 串进邻居函数 → 遇 ret 停
  D4（v3）条件分支两条臂都 push ⇒ pend 被污染 → 位宽取 pend 中最后一个 imm

另外新增：循环识别（后向跳转），循环体位长单独报，不与消息头相加。

用法:
  python -I tools/serialize_extract4.py 0x627d80
  python -I tools/serialize_extract4.py --all
"""
import re
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WB, WD = 0xB77B10, 0xB777C0
MAXDEPTH = 4


def body(b, va, maxlen=0x800):
    o = va - BASE
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    out = []
    for ins in md.disasm(b[o:o + maxlen], va):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return out


def width_of(pend):
    """位宽：pend 里最后一个立即数。没有 ⇒ 变长。"""
    for p in reversed(pend):
        if p[0] == "imm":
            return p[1]
    return None


def analyze(b, va, depth=0, seen=None):
    """返回 dict: pre(循环前位长), loop(循环体位长), loops, var, seq"""
    if seen is None:
        seen = set()
    if va in seen or depth > MAXDEPTH:
        return {"pre": 0, "loop": 0, "loops": 0, "var": False, "seq": []}
    seen.add(va)
    ins_list = body(b, va)
    if not ins_list:
        return {"pre": 0, "loop": 0, "loops": 0, "var": False, "seq": []}

    # 循环区间：后向跳转 [target, jmp_addr]
    ranges = []
    for ins in ins_list:
        if ins.mnemonic.startswith("j") and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t <= ins.address and va <= t < ins.address:
                ranges.append((t, ins.address))
    def in_loop(a):
        return any(lo <= a <= hi for lo, hi in ranges)

    pre = loop = 0
    var_pre = var_loop = False
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
        if m == "call" and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == WB:
                w = 5
                (loop if lp else pre).__class__  # noqa
                if lp:
                    loop += 5
                else:
                    pre += 5
                seq.append((lp, "bits", w, ins.address))
            elif t == WD:
                w = width_of(pend)
                if w is None:
                    if lp:
                        var_loop = True
                    else:
                        var_pre = True
                else:
                    if lp:
                        loop += w
                    else:
                        pre += w
                seq.append((lp, "data", w, ins.address))
            else:
                sub = analyze(b, t, depth + 1, seen)
                if sub["seq"] or sub["pre"] or sub["loop"]:
                    seq.append((lp, "call " + hex(t), None, ins.address))
                    seq.extend([(lp,) + tuple(s[1:]) for s in sub["seq"]])
                    if lp:
                        loop += sub["pre"] + sub["loop"]
                        var_loop = var_loop or sub["var"]
                    else:
                        pre += sub["pre"] + sub["loop"]
                        var_pre = var_pre or sub["var"]
            pend = []
            continue

    nloops = len({r[0] for r in ranges})
    return {"pre": pre, "loop": loop, "loops": nloops,
            "var": var_pre or var_loop, "seq": seq,
            "var_pre": var_pre, "var_loop": var_loop}


def report(va, d):
    print("===== %#010x =====" % va)
    for lp, kind, w, at in d["seq"]:
        print("%s %-14s %-6s @%#x" % (
            "  L" if lp else "   ", kind,
            ("%d" % w) if w is not None else "VAR", at))
    head = d["pre"]
    print("-- 头/循环外: %d 位 = %.2f 字节%s" % (
        head, head / 8.0, " (含变长)" if d["var_pre"] else ""))
    if d["loops"]:
        print("-- 循环体: %d 位 = %.2f 字节 × N%s" % (
            d["loop"], d["loop"] / 8.0, " (含变长)" if d["var_loop"] else ""))
    print()


def main():
    b = open(DUMP, "rb").read()
    if "--all" in sys.argv:
        # 从 vtable 表取全部 serialize（vtable[1]）
        import subprocess
        out = subprocess.run(
            [sys.executable, "-I", "tools/dwroom_serializers.py"],
            capture_output=True, text=True, encoding="latin1").stdout
        rows = []
        for line in out.splitlines():
            mm = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                          r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
            if mm:
                rows.append((mm.group(1), mm.group(4)))
        seen = set()
        for name, va in rows:
            if va in seen:
                continue
            seen.add(va)
            d = analyze(b, int(va, 16))
            print("%-46s pre=%-5d loop=%-5d x%d%s" % (
                name, d["pre"], d["loop"], d["loops"],
                "  VAR" if d["var"] else ""))
        return
    va = int(sys.argv[1], 0)
    report(va, analyze(b, va))


if __name__ == "__main__":
    main()

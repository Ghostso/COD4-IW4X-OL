#!/usr/bin/env python3
"""位流提取器 v3：严格按函数边界（遇到 ret 即停），跟进 call，
并标出循环体（同一函数体内的后向跳转）。输出每个 serialize 的
"单条消息位长"表达式，而不是一个错加在一起的数字。

用法: python -I tools/serialize_extract3.py 0x627d80 [--depth 3]
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import capstone.x86 as X

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WB, WD = 0xB77B10, 0xB777C0


def load():
    return open(DUMP, "rb").read()


def func_body(b, va, maxlen=0x600):
    """返回指令列表，遇到 ret/retn 立即停止。"""
    o = va - BASE
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    out = []
    for ins in md.disasm(b[o:o + maxlen], va):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return out


def seq_of(b, va, depth=0, maxdepth=4, seen=None, callers=()):
    """返回 [(kind, tag, nbits, at)]，kind in bits/data/var/call/loop。"""
    if seen is None:
        seen = set()
    if va in seen or depth > maxdepth:
        return [("recursive", None, None, va)]
    seen.add(va)
    ins_list = func_body(b, va)
    if not ins_list:
        return []

    # 找循环：后向跳转目标地址集合
    back_targets = set()
    for ins in ins_list:
        if ins.mnemonic.startswith("j") and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t <= ins.address:
                back_targets.add(t)

    out = []
    pend = []
    in_loop = False
    for ins in ins_list:
        if ins.address in back_targets:
            in_loop = True
        m, ops = ins.mnemonic, ins.operands
        if m == "push":
            if ops[0].type == X.X86_OP_IMM:
                pend.append(("imm", ops[0].imm))
            elif ops[0].type == X.X86_OP_MEM:
                pend.append(("mem", ops[0].mem.base and
                             ins.reg_name(ops[0].mem.base),
                             ops[0].mem.disp))
            else:
                pend.append(("reg", ins.reg_name(ops[0].reg)))
            pend = pend[-6:]
            continue
        if m == "call" and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == WB:
                out.append(("bits", pend[-1][1] if pend and pend[-1][0] == "imm"
                            else None, 5, ins.address))
            elif t == WD:
                nb = pend[-2] if len(pend) >= 2 else ("?",)
                ptr = pend[-1] if pend else ("?",)
                if nb[0] == "imm":
                    out.append(("data", None, nb[1], ins.address))
                else:
                    out.append(("var", None, None, ins.address))
            else:
                sub = seq_of(b, t, depth + 1, maxdepth, seen)
                if sub:
                    out.append(("call", hex(t), None, ins.address))
                    out.extend(sub)
            pend = []
            continue
    if in_loop:
        out.append(("has_loop", None, None, va))
    return out


def main():
    va = int(sys.argv[1], 0)
    maxdepth = 4
    if "--depth" in sys.argv:
        maxdepth = int(sys.argv[sys.argv.index("--depth") + 1])
    b = load()
    seq = seq_of(b, va, maxdepth=maxdepth)
    total = 0
    var = False
    loops = 0
    for kind, tag, nb, at in seq:
        if kind == "bits":
            total += 5
        elif kind == "data":
            total += nb
        elif kind == "var":
            var = True
        elif kind == "has_loop":
            loops += 1
        elif kind == "recursive":
            pass
        print("%-8s tag=%-4s nbits=%-6s @%#x" % (
            kind,
            ("0x%02x" % tag) if isinstance(tag, int) else tag,
            nb if nb is not None else "-", at))
    print("\n合计 %d 位 = %.2f 字节%s%s" % (
        total, total / 8.0,
        "（含变长，未定）" if var else "",
        "  ★含 %d 个循环体（每成员/每元素重复）" % loops if loops else ""))


if __name__ == "__main__":
    main()

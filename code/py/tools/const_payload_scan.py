#!/usr/bin/env python3
"""扫描所有 dwRoomMessage serialize，找出"写入的载荷来自常量/全局"的位置。

判据：writeData 之前最近的 push 是立即数（= 全局地址/常量指针），
而不是 lea reg,[esi+...]（= 对象字段）。

输出：可 100% 静态预测的字节。
用法: python -I tools/const_payload_scan.py
"""
import re
import subprocess
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def scan(b, va):
    """返回 [(tag, nbits, src_kind, src_desc, at)]，src_kind in obj/const/stack"""
    o = va - E.BASE
    out = []
    tag = None
    pend = []            # push 参数栈
    lea_map = {}         # reg -> (base, disp) 最近一次 lea 写入
    for ins in md.disasm(b[o:o + 0x1000], va):
        m, ops = ins.mnemonic, ins.operands
        if m.startswith("ret"):
            break
        if m == "lea" and ops and ops[-1].type == X.X86_OP_MEM:
            mem = ops[-1].mem
            dst = md.reg_name(ops[0].reg)
            lea_map[dst] = (md.reg_name(mem.base) if mem.base else None,
                            mem.disp)
        if m == "push":
            if ops and ops[0].type == X.X86_OP_IMM:
                pend.append(("imm", ops[0].imm))
            elif ops and ops[0].type == X.X86_OP_REG:
                r = md.reg_name(ops[0].reg)
                pend.append(("reg", r, lea_map.get(r)))
            elif ops and ops[0].type == X.X86_OP_MEM:
                pend.append(("mem", md.reg_name(ops[0].mem.base)
                             if ops[0].mem.base else None, ops[0].mem.disp))
            else:
                pend.append(("?",))
            pend = pend[-6:]
            continue
        if m == "call" and ops and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == E.WB:
                tag = pend[-1][1] if pend and pend[-1][0] == "imm" else None
            elif t == E.WD:
                nb = pend[-2][1] if len(pend) >= 2 and pend[-2][0] == "imm" \
                    else None
                ptr = pend[-1] if pend else ("?",)
                kind, desc = classify(ptr)
                out.append((tag, nb, kind, desc, ins.address))
                tag = None
            pend = []
            continue
    return out


def classify(ptr):
    if ptr[0] == "imm":
        return "const", "%#x" % ptr[1]
    if ptr[0] == "reg":
        lz = ptr[2]
        if lz and lz[0] in ("esi", "edi"):
            return "obj", "[%s+%#x]" % lz
        if lz and lz[0] == "ebp":
            return "stack", "[ebp%+#x]" % lz[1]
        if lz:
            return "obj2", "[%s+%#x]" % lz
        return "reg", ptr[1]
    if ptr[0] == "mem":
        return "mem", "[%s+%#x]" % (ptr[1], ptr[2])
    return "?", "-"


def main():
    b = open(E.DUMP, "rb").read()
    rows = E.rows_from_vtable()
    rows.append(("dwRoomMessageP2PInfo", "0x627fc0", "0x6280b0"))
    seen = set()
    for name, ser, _ in rows:
        va = int(ser, 16)
        if va in seen:
            continue
        seen.add(va)
        items = scan(b, va)
        if not items:
            continue
        stackish = [x for x in items if x[2] in ("stack", "obj2", "?")]
        print("===== %s (%#x) =====" % (name, va))
        for tag, nb, kind, desc, at in items:
            mark = "  ★常量?" if kind in ("stack", "obj2", "?") else ""
            print("  tag=%-5s bits=%-5s %-6s %-16s @%#x%s" % (
                ("0x%02x" % tag) if tag is not None else "?",
                nb if nb is not None else "VAR", kind, desc, at, mark))
        print()


if __name__ == "__main__":
    main()

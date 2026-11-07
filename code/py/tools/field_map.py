#!/usr/bin/env python3
"""提取每个位流写入点的 (tag, 位宽, 源字段偏移) 三元组。
源偏移取 writeData 之前最近的一条 lea reg,[base+disp] 或 movzx reg,[base+disp]。

用法: python -I tools/field_map.py 0x623880
      python -I tools/field_map.py 0x627ea0
      python -I tools/field_map.py 0x627d80
"""
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dump(va, tagc=E.WB, datc=E.WD):
    b = open(E.DUMP, "rb").read()
    o = va - E.BASE
    ins_list = []
    for ins in md.disasm(b[o:o + 0x1000], va):
        ins_list.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    rows = []
    cur_tag = None
    last_off = None
    pend = []
    for ins in ins_list:
        m, ops = ins.mnemonic, ins.operands
        # 记录源偏移
        if m in ("lea", "movzx", "movsx") and ins.operands:
            try:
                mem = ins.operands[-1].mem
                if mem.base and md.reg_name(mem.base) in (
                        "edi", "esi", "ebx", "eax", "edx", "ecx"):
                    base = md.reg_name(mem.base)
                    last_off = (base, mem.disp)
            except Exception:
                pass
        if m == "push":
            pend.append(ops[0].imm if ops and ops[0].type == X.X86_OP_IMM
                        else None)
            continue
        if m == "call" and ops and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == tagc:
                cur_tag = pend[-1] if pend and pend[-1] is not None else None
                last_off = None
            elif t == datc:
                w = None
                for p in reversed(pend):
                    if p is not None:
                        w = p
                        break
                rows.append((cur_tag, w, last_off))
                cur_tag = None
                last_off = None
            pend = []
            continue
    print("===== %#010x =====" % va)
    print("%-6s %-6s %-18s" % ("tag", "bits", "源字段"))
    total = 0
    for tag, w, off in rows:
        ofs = ("[%s+%#x]" % off) if off else "-"
        print("%-6s %-6s %-18s" % (
            ("0x%02x" % tag) if tag is not None else "?",
            w if w is not None else "VAR", ofs))
        if isinstance(w, int):
            total += w
        if tag is not None:
            total += 5
    print("-- 小计 %d 位" % total)


if __name__ == "__main__":
    va = int(sys.argv[1], 0)
    is_read = "--read" in sys.argv
    dump(va, E.RB if is_read else E.WB, E.RD if is_read else E.WD)

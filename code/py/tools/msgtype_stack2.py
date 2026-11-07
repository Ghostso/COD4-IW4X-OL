#!/usr/bin/env python3
"""类型号注册点 v2：用 capstone 精确解析，只在**相邻指令窗口**内配对。

规则：
  对每条 `mov dword [ebp + d], <vfptr>`，
  在同函数内、**紧随其后 8 条指令 / 之前 2 条**范围里找
  `mov dword [ebp + d + 4], <imm>`（imm <= 0xFF）。

用法: python -I tools/msgtype_stack2.py
"""
import re
import subprocess
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def classes():
    out = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    r = []
    for line in out.splitlines():
        m = re.match(r"^(\S+)\s+(0x[0-9a-f]+)", line)
        if m:
            r.append((m.group(1), int(m.group(2), 16)))
    return r


def is_mem_local(ins, base_name, disp):
    op = ins.operands[0]
    return (op.type == X.X86_OP_MEM and op.mem.base != 0 and
            ins.reg_name(op.mem.base) == base_name and
            op.mem.disp == disp and op.size == 4)


def main():
    b = open(DUMP, "rb").read()
    cls = classes()
    vf2name = {}
    for name, col in cls:
        vf2name[col + 4] = name
        vf2name[col] = name

    md.skipdata = True
    lo, hi = 0x624000 - BASE, 0x640000 - BASE
    ins_list = list(md.disasm(b[lo:hi], 0x624000))
    print("解码 %d 条" % len(ins_list))

    # 建索引：按地址
    idx = {ins.address: i for i, ins in enumerate(ins_list)}
    res = {}
    for i, ins in enumerate(ins_list):
        if ins.mnemonic != "mov" or len(ins.operands) != 2:
            continue
        dst, src = ins.operands
        if (dst.type != X.X86_OP_MEM or src.type != X.X86_OP_IMM or
                dst.size != 4 or dst.mem.base == 0):
            continue
        if src.imm not in vf2name:
            continue
        rg = ins.reg_name(dst.mem.base)
        d = dst.mem.disp
        name = vf2name[src.imm]
        # 向后 8 条 / 向前 2 条
        best = None
        for j in range(max(0, i - 2), min(len(ins_list), i + 9)):
            ins2 = ins_list[j]
            if ins2.mnemonic != "mov" or len(ins2.operands) != 2:
                continue
            d2, s2 = ins2.operands
            if (d2.type != X.X86_OP_MEM or s2.type != X.X86_OP_IMM or
                    d2.size != 4 or d2.mem.base == 0):
                continue
            if ins2.reg_name(d2.mem.base) != rg or d2.mem.disp != d + 4:
                continue
            if not (0 <= s2.imm <= 0xFF):
                continue
            dist = abs(j - i)
            if best is None or dist < best[0]:
                best = (dist, s2.imm, ins2.address)
        if best and name not in res:
            res[name] = (best[1], ins.address, best[2], src.imm)

    print("\n=== 每类类型号（相邻指令配对）===")
    for name, col in cls:
        r = res.get(name)
        print("%-46s 类型号 = %-22s %s" % (
            name, ("%d (0x%02x)" % (r[0], r[0])) if r else "?",
            ("vfptr@%#x type@%#x" % (r[1], r[2])) if r else ""))
    ok = [n for n, _ in cls if n in res]
    print("\n命中 %d / %d" % (len(ok), len(cls)))
    with open("_byte_papers/msgtype_stack2.txt", "w", encoding="utf-8") as f:
        f.write("class\ttype\tvfptr_site\ttype_site\tvfptr\n")
        for name, col in cls:
            r = res.get(name)
            f.write("%s\t%s\t%s\t%s\t%#x\n" % (
                name, r[0] if r else "",
                hex(r[1]) if r else "", hex(r[2]) if r else "", col + 4))


if __name__ == "__main__":
    main()

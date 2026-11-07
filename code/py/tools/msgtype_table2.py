#!/usr/bin/env python3
"""类 -> 类型号：双向配对。

MSVC 构造函数里两条相邻的写：
   mov dword ptr [reg+4], <typeNo>     ; 类型号（常在 vfptr 之前！）
   mov dword ptr [reg],   <vfptr>      ; vfptr = COL + 4

所以：先扫全部 [reg+4]=imm，再**向前后**各 0x60 字节找同寄存器的
      mov [reg], imm 且 imm 属于 {COL+4} 集合。
"""
import re
import struct
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
        m = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                     r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if m:
            r.append((m.group(1), int(m.group(2), 16), int(m.group(4), 16)))
    return r


def main():
    b = open(DUMP, "rb").read()
    cls = classes()
    vf2name = {col + 4: name for name, col, _ in cls}
    ser2name = {ser: name for name, _, ser in cls}

    lo, hi = 0x624000 - BASE, 0x640000 - BASE
    md.skipdata = True
    ins_all = list(md.disasm(b[lo:hi], 0x624000))

    # 索引：地址 -> 指令
    addr_ins = {i.address: i for i in ins_all}

    typ_writes = []   # (addr, reg, typeNo, size)
    vf_writes = {}    # addr -> (reg, imm)
    for ins in ins_all:
        if ins.mnemonic != "mov" or len(ins.operands) != 2:
            continue
        dst, src = ins.operands
        if dst.type != X.X86_OP_MEM or src.type != X.X86_OP_IMM:
            continue
        rg = md.reg_name(dst.mem.base)
        if dst.mem.disp == 4 and dst.size in (1, 4):
            typ_writes.append((ins.address, rg, src.imm, dst.size))
        elif dst.mem.disp == 0 and dst.size == 4:
            vf_writes[ins.address] = (rg, src.imm)

    print("=== [reg+4]=imm 共 %d 处 ===" % len(typ_writes))
    results = []
    for addr, rg, imm, size in typ_writes:
        # 前后各找 0x60 字节内、同寄存器的 vfptr 写
        cand = None
        for a2, (rg2, imm2) in vf_writes.items():
            if rg2 != rg:
                continue
            if abs(a2 - addr) <= 0x60 and imm2 in vf2name:
                if cand is None or abs(a2 - addr) < abs(cand[0] - addr):
                    cand = (a2, imm2)
        name = vf2name.get(cand[1]) if cand else None
        results.append((name, imm, size, addr, cand))
        print("%#010x  [%s+4]=%d(%d字节)  vfptr=%s  => %s" % (
            addr, rg, imm, size,
            ("%#x@%#x" % (cand[1], cand[0])) if cand else "-",
            name or "?"))

    print("\n=== 类 -> 类型号 ===")
    got = {}
    for name, imm, size, addr, cand in results:
        if name and name not in got:
            got[name] = imm
    for name, col, ser in cls:
        t = got.get(name)
        print("%-46s 类型号 = %s" % (
            name, ("%d (0x%02x)" % (t, t)) if t is not None else "?"))
    print("\n命中 %d / %d" % (len(got), len(cls)))
    with open("_byte_papers/msgtype_table.txt", "w", encoding="utf-8") as f:
        f.write("class\ttype\tvtable\n")
        for name, col, ser in cls:
            t = got.get(name)
            f.write("%s\t%s\t%#x\n" % (
                name, t if t is not None else "", col))


if __name__ == "__main__":
    main()

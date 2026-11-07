#!/usr/bin/env python3
"""dwRoomMessage 类 -> 类型号（[obj+4] 常量）对照表。

原理（MSVC x86 /O2）:
  构造函数形如:
      mov dword ptr [reg], <vfptr>      ; vfptr = COL + 4
      mov dword ptr [reg+4], <typeNo>   ; ★ 消息类型号
  其中 COL = dwroom_serializers.py 报的 "vtable"（TypeDescriptor 指针所在处）。

做法:
  1. 取 50 个类的 COL 地址
  2. 全镜像扫 "C7 /0 imm32"，imm32 == COL+4 => 找到构造函数装填点
  3. 从该点前后 0x30 字节内找 "C7 4x 04 imm32" => 类型号
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
    colmap = {col: name for name, col, _ in cls}
    vfmap = {col + 4: name for name, col, _ in cls}

    # 扫所有 mov dword [reg], imm32
    lo, hi = 0x624000 - BASE, 0x640000 - BASE
    md.skipdata = True
    found = {}
    for ins in md.disasm(b[lo:hi], 0x624000):
        if ins.mnemonic != "mov" or len(ins.operands) != 2:
            continue
        dst, src = ins.operands
        if dst.type != X.X86_OP_MEM or src.type != X.X86_OP_IMM:
            continue
        if dst.mem.disp != 0 or dst.size != 4:
            continue
        if src.imm not in vfmap:
            continue
        name = vfmap[src.imm]
        found.setdefault(name, []).append((ins.address,
                                           md.reg_name(dst.mem.base)))

    print("=== 构造函数 vfptr 装填点 ===")
    for name, col, ser in cls:
        locs = found.get(name)
        desc = ("%#x(reg=%s)" % (locs[0][0], locs[0][1])) if locs else "-"
        print("%-46s COL=%#010x  ser=%#010x  装填点=%s" % (
            name, col, ser, desc))
    print("\n共找到 %d 个类的构造函数" % len(found))

    # 对每个装填点，向后扫 0x40 字节找 [reg+4]=imm
    print("\n=== 类 -> 类型号 ===")
    results = []
    for name, col, ser in cls:
        locs = found.get(name)
        if not locs:
            continue
        for va, rg in locs:
            o = va - BASE
            try:
                ins_list = list(md.disasm(b[o:o + 0x50], va))
            except Exception:
                continue
            typ = None
            for ins in ins_list:
                if ins.mnemonic == "mov" and len(ins.operands) == 2:
                    dst, src = ins.operands
                    if (dst.type == X.X86_OP_MEM and src.type ==
                            X.X86_OP_IMM and dst.mem.disp == 4 and
                            dst.size in (1, 4) and
                            md.reg_name(dst.mem.base) == rg):
                        typ = src.imm
                        break
                if ins.mnemonic.startswith("ret"):
                    break
            results.append((name, typ, va))
            break
    for name, typ, va in results:
        print("%-46s 类型号 = %-6s (0x%02x)  @ctor %#x" % (
            name, typ if typ is not None else "?",
            typ if typ is not None else 0, va))
    got = [t for _, t, _ in results if t is not None]
    print("\n有类型号 %d / %d 类" % (len(got), len(cls)))
    from collections import Counter
    dup = {k: v for k, v in Counter(got).items() if v > 1}
    if dup:
        print("★ 重复类型号:", dup)
    with open("_byte_papers/msgtype_table.txt", "w", encoding="utf-8") as f:
        for name, typ, va in results:
            f.write("%s\t%s\t%#x\n" % (name, typ, va))


if __name__ == "__main__":
    main()

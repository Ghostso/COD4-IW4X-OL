#!/usr/bin/env python3
"""138: find 'mov reg,[reg+disp]' or 'call [reg+disp]' style accesses to a given struct offset.
Also find 'call [reg+disp]' indirect dispatch (FF /2).
用法: s138_disp.py <disp_hex> [--call]
默认打印所有 'mov/lea/call [reg+disp]' 命中(带 modrm 解码), 过滤 disp 精确匹配。
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

# disassemble whole .text once from 0x401000
TEXT_LO = 0x401000
TEXT_HI = 0x401000 + 0x8a689a

disp = int(sys.argv[1], 0)
want_call = "--call" in sys.argv


def run(off_lo, off_hi):
    code = d[off_lo - VA:off_hi - VA]
    count = 0
    for ins in md.disasm(code, off_lo):
        # only consider memory operand with displacement
        if "[" not in ins.op_str:
            continue
        m = re.search(r"\[[^\]]*?\+\s*(0x[0-9a-f]+)\]", ins.op_str)
        if not m:
            continue
        try:
            dv = int(m.group(1), 16)
        except ValueError:
            continue
        if dv != disp:
            continue
        if want_call:
            if ins.mnemonic not in ("call", "jmp"):
                continue
        # skip rip-relative style absolute (no base)
        if re.match(r"\[0x", ins.op_str):
            continue
        count += 1
        print("0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(),
                                       ins.mnemonic, ins.op_str))
    return count


c = run(TEXT_LO, TEXT_HI)
print("TOTAL %d" % c)

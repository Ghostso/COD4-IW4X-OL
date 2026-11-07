# -*- coding: utf-8 -*-
"""015: find sockaddr_in construction.

Heuristic: a 16-bit store of immediate 2 (AF_INET) into [reg+disp] followed
within N instructions by a 16-bit store into [same_reg + disp + 2] (sin_port)
and a 32-bit store into [same_reg + disp + 4] (sin_addr).
"""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG  # noqa

LO = int(sys.argv[1], 16) if len(sys.argv) > 1 else BASE
HI = int(sys.argv[2], 16) if len(sys.argv) > 2 else END
WIN = int(sys.argv[3]) if len(sys.argv) > 3 else 14


def sweep(lo, hi):
    pos = lo
    while pos < hi:
        code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
        ins = next(MD.disasm(code, pos), None)
        if ins is None or ins.size == 0:
            pos += 1
            continue
        yield ins
        pos += ins.size


def mem_of(ins):
    for i, op in enumerate(ins.operands):
        if op.type == X86_OP_MEM:
            return i, op
    return None, None


def main():
    buf = []
    hits = 0
    for ins in sweep(LO, HI):
        buf.append(ins)
        if len(buf) > WIN:
            buf.pop(0)
        if len(buf) < 2:
            continue
        # candidate: instr that sets a word to 2
        if not (ins.mnemonic in ("mov", "or", "and", "xor", "add")
                and ins.operands and ins.operands[0].type == X86_OP_MEM
                and ins.operands[0].size == 2
                and len(ins.operands) > 1 and ins.operands[1].type == X86_OP_IMM
                and ins.operands[1].imm == 2):
            continue
        m = ins.operands[0].mem
        if m.index != 0 or m.base == 0:
            continue
        base_reg = ins.reg_name(m.base)
        fam = m.disp
        port_seen = None
        addr_seen = None
        for later in buf[buf.index(ins) + 1:]:
            j, op = mem_of(later)
            if op is None or j != 0 or op.mem.index != 0 or op.mem.base != m.base:
                continue
            if later.operands[0].size == 2 and op.mem.disp == fam + 2:
                port_seen = later
            if later.operands[0].size == 4 and op.mem.disp == fam + 4:
                addr_seen = later
        if port_seen is None:
            continue
        hits += 1
        print("==== sockaddr candidate fam@[%s+0x%X] af_inet at 0x%08X" % (base_reg, fam, ins.address))
        for b in buf:
            mark = "  <<" if b in (ins, port_seen, addr_seen) else ""
            print("     0x%08X  %-22s %s %s%s" % (b.address, b.bytes.hex(),
                                                  b.mnemonic, b.op_str, mark))
        print("     port store: %s   addr store: %s"
              % (("%s %s @0x%08X" % (port_seen.mnemonic, port_seen.op_str, port_seen.address)) if port_seen else None,
                 ("%s %s @0x%08X" % (addr_seen.mnemonic, addr_seen.op_str, addr_seen.address)) if addr_seen else None))
    print("total candidates %d" % hits)


main()

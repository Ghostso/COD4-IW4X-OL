#!/usr/bin/env python3
"""定位大厅状态机的分派跳转表：在 0x7ee900-0x7ef500 区间找 jmp [reg*4+table]。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000

from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def main():
    b = open(DUMP, "rb").read()
    lo, hi = 0x7ee800, 0x7ef600
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    o = lo - BASE
    for ins in md.disasm(b[o:o + (hi - lo)], lo):
        if ins.id == 0:
            continue
        try:
            ops = ins.operands
        except Exception:
            continue
        if ins.mnemonic == "jmp" and ops and ops[0].type == 3:
            m = ops[0].mem
            if m.index != 0 and m.disp > 0x400000:
                print("jmp table @ %#010x -> disp=%#x scale=%d index=%s"
                      % (ins.address, m.disp, m.scale, ins.reg_name(m.index)))
                # dump table
                to = m.disp - BASE
                for i in range(12):
                    v = struct.unpack_from("<I", b, to + i * 4)[0]
                    print("     [%d] %#010x" % (i, v))


if __name__ == "__main__":
    main()

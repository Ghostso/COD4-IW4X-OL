# -*- coding: utf-8 -*-
"""0xB9A5xx disassembly with capstone: what does the validator actually check?"""
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    o = 0xB9A540 - BASE
    code = d[o:o+0x140]
    for ins in md.disasm(code, 0xB9A540):
        print("0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
except ImportError:
    print("capstone missing")

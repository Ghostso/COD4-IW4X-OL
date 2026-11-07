import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

import capstone
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

for va in range(0x62A000, 0x636000):
    code = pe.read(va, 7)
    for ins in cs.disasm(code, va):
        if ins.mnemonic == "mov" and "+ 0x1c" in ins.op_str:
            dst = ins.op_str.split(",")[0]
            if "[" in dst:
                print(f"Write at 0x{va:X}: {ins.mnemonic} {ins.op_str}")
        break

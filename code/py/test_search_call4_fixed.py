import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

refs = pe.find_dword(0x82E13FC)
for off, va in refs:
    raw = pe.read(va, 35)
    insns = list(cs.disasm(raw, va))
    for ins in insns:
        if ins.mnemonic == "call" and ("+ 4" in ins.op_str or "+ 0x4" in ins.op_str):
            print(f"Match call at 0x{ins.address:08X} in func around 0x{va:X}: {ins.mnemonic} {ins.op_str}")
            for prev in insns:
                print(f"  0x{prev.address:08X}  {prev.mnemonic} {prev.op_str}")

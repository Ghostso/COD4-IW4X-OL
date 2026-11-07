import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

for va in [0x62E735, 0x634DF5]:
    print(f"=== Disasm around 0x{va:X} ===")
    raw = pe.read(va, 40)
    for ins in cs.disasm(raw, va):
        print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

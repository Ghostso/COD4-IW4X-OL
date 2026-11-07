import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

target = 0x62CD50
raw = pe.read(0x62CC80, target - 0x62CC80 + 30)
for ins in cs.disasm(raw, 0x62CC80):
    print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

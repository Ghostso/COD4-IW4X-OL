import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

targets = [0x63A9ED, 0x63BE75, 0x63C1BF, 0x63C2FF, 0x605499, 0x752945]
for va in targets:
    print(f"=== Ref at 0x{va:X} ===")
    raw = pe.read(va - 15, 30)
    for ins in cs.disasm(raw, va - 15):
        print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

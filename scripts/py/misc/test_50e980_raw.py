import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
sec = pe.section_of(0x50E980)
print("Section for 0x50E980:", sec)
raw = pe.read(0x50E970, 64)
print("Raw bytes at 0x50E970:", raw[:32].hex())
import capstone
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for ins in cs.disasm(raw, 0x50E970):
    print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

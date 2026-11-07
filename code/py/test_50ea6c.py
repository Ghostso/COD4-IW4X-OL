import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

print("=== Disasm 0x50EA6C ===")
raw = pe.read(0x50EA6C, 64)
for ins in cs.disasm(raw, 0x50EA6C):
    print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

print("\n=== Disasm 0x50EB80 (callback?) ===")
raw2 = pe.read(0x50EB80, 64)
for ins in cs.disasm(raw2, 0x50EB80):
    print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

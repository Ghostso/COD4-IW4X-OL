import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

for test_va in range(0x634DF0, 0x634C00, -1):
    b = pe.read(test_va, 3)
    if b == b"\x55\x8b\xec" or (pe.read(test_va-1, 1) in [b"\xcc", b"\xc3"] and b[0] in [0x55, 0x56, 0x53, 0x8b]):
        func_start = test_va
        break

print(f"Function containing 0x634DF5 starts at 0x{func_start:X}")
raw = pe.read(func_start, 120)
for ins in cs.disasm(raw, func_start):
    print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

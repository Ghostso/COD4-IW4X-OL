import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Find function start
target = 0x634E0C
func_start = None
for va in range(target, target - 0x500, -1):
    raw = pe.read(va, 3)
    if raw == b"\x55\x8b\xec": # push ebp; mov ebp, esp
        func_start = va
        break

print(f"Function start: 0x{func_start:X}")
if func_start:
    raw = pe.read(func_start, target - func_start + 30)
    for ins in cs.disasm(raw, func_start):
        if ins.address >= 0x634DE0:
            print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

target = 0x634E0C
prev_ret = None
for va in range(target, target - 0x300, -1):
    b = pe.read(va, 1)
    if b in [b"\xc3", b"\xc2", b"\xcc"]:
        prev_ret = va
        break

print(f"Prev ret/int3 at: 0x{prev_ret:X}")
# Disassemble from after prev_ret up to target+20
start = prev_ret + 1
while pe.read(start, 1) == b"\xcc":
    start += 1
print(f"Function starts at: 0x{start:X}")
raw = pe.read(start, target - start + 40)
for ins in cs.disasm(raw, start):
    print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Find all references to 0x82E13FC
refs = pe.find_dword(0x82E13FC)
print(f"Total refs to matching singleton (0x82E13FC): {len(refs)}")

for off, va in refs:
    # disassemble 15 instructions starting from va
    raw = pe.read(va, 40)
    insns = list(cs.disasm(raw, va))
    # look for call [eax + ...] or call [edx + ...]
    for ins in insns[:6]:
        if "call" in ins.mnemonic:
            print(f"Ref at 0x{va:X}: {ins.mnemonic} {ins.op_str}")

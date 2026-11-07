import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Search for writes to [esi+0x1c] or [ecx+0x1c] or [edi+0x1c] or [ebx+0x1c] in 0x62A000..0x636000
import capstone
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

for va in range(0x62A000, 0x636000):
    code = pe.read(va, 7)
    for ins in cs.disasm(code, va):
        if ins.mnemonic == "mov" and "+ 0x1c]" in ins.op_str and ins.op_str.startswith("["):
            print(f"Write at 0x{va:X}: {ins.mnemonic} {ins.op_str}")
        break

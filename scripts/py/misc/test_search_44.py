import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Search for any instructions calling [reg + 0x44] where reg is vtable of matching singleton
# Or calling [reg + 0x08] on the sub-interface at [matching_singleton + 0x3C]
targets = []
for sec in pe.sections:
    if not (sec.chars & 0x20000000): continue
    data = pe.data[sec.rawptr : sec.rawptr + sec.rawsize]
    base_va = pe.base + sec.vaddr
    
    # ff 50..57 44 (call [reg+44h])
    for off in range(len(data) - 3):
        if data[off] == 0xff and (data[off+1] in [0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57]) and data[off+2] == 0x44:
            va = base_va + off
            targets.append(va)

print(f"Total candidate call [reg+0x44]: {len(targets)}")
for va in targets:
    # check if preceded by reading [0x82E13FC]
    raw = pe.read(va - 25, 30)
    insns = list(cs.disasm(raw, va - 25))
    has_singleton = any("82e13fc" in ins.op_str.lower() for ins in insns)
    if has_singleton:
        print(f"=== Hit at 0x{va:X} ===")
        for ins in insns:
            print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")

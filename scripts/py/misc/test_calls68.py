import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Let's search for instructions with displacement 0x68 that are calls
# Capstone approach: disassemble all functions or search for opcode sequences
import capstone
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
cs.detail = True

candidates = []
for sec in pe.sections:
    if not (sec.chars & 0x20000000):
        continue
    data = pe.data[sec.rawptr : sec.rawptr + sec.rawsize]
    base_va = pe.base + sec.vaddr
    
    # scan for byte patterns:
    # ff 50..57 68 (call [reg+68h])
    # ff 90..97 68 00 00 00 (call [reg+00000068h])
    for off in range(len(data) - 6):
        b0 = data[off]
        b1 = data[off+1]
        b2 = data[off+2]
        if b0 == 0xff:
            if (b1 in [0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57]) and b2 == 0x68:
                va = base_va + off
                candidates.append(va)
            elif (b1 in [0x90, 0x91, 0x92, 0x93, 0x95, 0x96, 0x97]) and b2 == 0x68 and data[off+3:off+6] == b"\x00\x00\x00":
                va = base_va + off
                candidates.append(va)

print(f"Total candidate call [reg+0x68] VAs: {len(candidates)}")
# Filter candidates by disassembling 1 instruction at va to verify it's a real valid instruction
valid_calls = []
for va in candidates:
    code = pe.read(va, 7)
    for ins in cs.disasm(code, va):
        if ins.mnemonic == "call" and "+ 0x68" in ins.op_str:
            valid_calls.append((va, ins.op_str))
        break

print(f"Valid call [reg+0x68]: {len(valid_calls)}")
for va, op in valid_calls:
    print(f"  0x{va:X}: call {op}")

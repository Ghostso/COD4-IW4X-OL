import os, capstone

path = "unpacked_link_chunk.bin"
if not os.path.exists(path):
    path = os.path.join("REF_LOBBY_KIT", "unpacked_link_chunk.bin")

print(f"Reading from {path}")
with open(path, "rb") as f:
    data = f.read()

print(f"Data length: {len(data)} bytes")

base_va = 0x00617305
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Disassemble all instructions
insns = list(md.disasm(data, base_va))

# Find functions (preceded by ret/int3 or standard function prologues)
funcs = []
for i in range(len(insns)):
    ins = insns[i]
    # Check for function start:
    # 1. ret/int3 before it
    # 2. or push ebp; mov ebp, esp
    # 3. or fldz (SV_UnlinkEntity at 0x00617B05)
    is_start = False
    if i == 0:
        is_start = True
    elif insns[i-1].mnemonic in ['ret', 'retn'] or insns[i-1].bytes in [b'\xcc', b'\xc3']:
        is_start = True
    elif ins.mnemonic == 'push' and ins.op_str == 'ebp' and i + 1 < len(insns) and insns[i+1].mnemonic == 'mov' and 'ebp, esp' in insns[i+1].op_str:
        is_start = True
    elif ins.address == 0x00617B05:
        is_start = True
    
    if is_start:
        funcs.append((ins.address, ins.address - 0x00400000, i))

print(f"\nFound {len(funcs)} functions in the 4KB chunk:")
for va, rva, idx in funcs:
    f_ins = insns[idx:idx+6]
    f_code = " ".join(f"{x.mnemonic} {x.op_str};" for x in f_ins)
    raw = data[va - base_va : va - base_va + 12].hex()
    mark = "  <-- SV_UnlinkEntity" if va == 0x00617B05 else ""
    print(f"  VA 0x{va:08X} (RVA 0x{rva:06X}): {raw} | {f_code}{mark}")

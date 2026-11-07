import capstone

with open(r"REF_LOBBY_KIT\unpacked_link_chunk.bin", "rb") as f:
    data = f.read()

base_va = 0x00617305
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

print("Scanning for function starts and instructions...")
i = 0
while i < len(data):
    # try disassembling from i
    curr_va = base_va + i
    insns = list(md.disasm(data[i:i+64], curr_va))
    if not insns:
        i += 1
        continue
    
    ins = insns[0]
    # Check for interesting instructions or function prologues
    # Prologue: push ebp; mov ebp, esp
    # Or sub esp, ... / and esp, 0xfffffff8
    raw = data[i:i+16].hex()
    if ins.mnemonic == 'push' and ins.op_str == 'ebp':
        print(f"Prologue at 0x{curr_va:08X} (RVA 0x{curr_va - 0x400000:06X}): {raw[:16]}")
        for sub_ins in insns[:6]:
            print(f"    0x{sub_ins.address:08X}: {sub_ins.mnemonic:8} {sub_ins.op_str}")
    elif curr_va == 0x00617B05:
        print(f"SV_UnlinkEntity at 0x{curr_va:08X} (RVA 0x{curr_va - 0x400000:06X})")
    
    i += ins.size

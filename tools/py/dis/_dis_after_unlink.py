import capstone

with open(r"REF_LOBBY_KIT\unpacked_link_chunk.bin", "rb") as f:
    data = f.read()

base_va = 0x00617305
start_va = 0x00617BB0
start_off = start_va - base_va

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

chunk = data[start_off : start_off + 600]
print(f"Disassembling 600 bytes from VA 0x{start_va:08X} (offset 0x{start_off:X}):")
for ins in md.disasm(chunk, start_va):
    mark = ""
    if ins.mnemonic in ['ret', 'retn']:
        mark = "  <-- RET"
    elif 'link' in ins.op_str.lower():
        mark = "  <-- LINK"
    print("  0x%08X: %-10s %-25s %s" % (ins.address, ins.mnemonic, ins.op_str, mark))

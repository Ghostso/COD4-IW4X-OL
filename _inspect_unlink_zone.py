import capstone

with open(r"REF_LOBBY_KIT\unpacked_link_chunk.bin", "rb") as f:
    data = f.read()

base_va = 0x00617305
target_va = 0x00617B05
target_off = target_va - base_va # 0x800

print(f"Target offset: 0x{target_off:X} (VA 0x{target_va:X})")
print("Bytes at target (SV_UnlinkEntity):", data[target_off:target_off+16].hex())

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Disassemble backwards from 0x800 to find the previous function
print("\n--- 256 bytes BEFORE SV_UnlinkEntity (0x617A05 .. 0x617B05) ---")
before_chunk = data[target_off - 256 : target_off]
for ins in md.disasm(before_chunk, target_va - 256):
    print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))

print("\n--- 256 bytes AFTER SV_UnlinkEntity (0x617B05 .. 0x617C05) ---")
after_chunk = data[target_off : target_off + 256]
for ins in md.disasm(after_chunk, target_va):
    print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))

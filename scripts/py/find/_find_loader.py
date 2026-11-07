import pefile, capstone

dll = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\Localnetworking.Ayria32"
pe = pefile.PE(dll)
base = pe.OPTIONAL_HEADER.ImageBase

with open(dll, "rb") as f:
    d = f.read()

s = b"Loaded Localnet32 plugin"
idx = d.find(s)
print(f"String at 0x{idx:X}")
va = base + pe.get_rva_from_offset(idx)
print(f"VA: 0x{va:X}")

pattern = va.to_bytes(4, "little")
pos = 0
refs = []
while True:
    i = d.find(pattern, pos)
    if i == -1: break
    refs.append(i)
    pos = i + 1

print(f"References at file offsets: {[hex(x) for x in refs]}")
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for off in refs:
    start = max(0, off - 80)
    chunk = d[start:off+60]
    va_chunk = base + pe.get_rva_from_offset(start)
    print(f"\n--- Disassembly around reference at 0x{off:X} ---")
    for ins in md.disasm(chunk, va_chunk):
        print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))

import pefile, capstone

dll_path = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32"
pe = pefile.PE(dll_path)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

with open(dll_path, "rb") as f:
    d = f.read()

# Disassemble from 0x1020AC20 to 0x1020AE00
start_va = 0x1020AC20
start_off = pe.get_offset_from_rva(start_va - base)

chunk = d[start_off : start_off + 300]
print(f"Disassembling EngineBindings::bind guards starting at 0x{start_va:X}:")
for ins in md.disasm(chunk, start_va):
    mark = ""
    if '1020bc' in ins.op_str:
        mark = "  <-- JUMP TO FAILURE"
    elif ins.mnemonic == 'call':
        mark = "  <-- CALL"
    print("  0x%08X: %-10s %-30s%s" % (ins.address, ins.mnemonic, ins.op_str, mark))

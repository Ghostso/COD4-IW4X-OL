import pefile, capstone

dll_path = r"_e1_regression\ol-mod-olfinal\build\bin\release\CodolGameServer.Localnet32"
pe = pefile.PE(dll_path)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

with open(dll_path, "rb") as f:
    d = f.read()

for off in [0x4d95b, 0x1ca758, 0x20a010]:
    print(f"\n=== Offset 0x{off:X} (VA 0x{base + pe.get_rva_from_offset(off):X}) ===")
    start = max(0, off - 32)
    end = min(len(d), off + 48)
    va = base + pe.get_rva_from_offset(start)
    for ins in md.disasm(d[start:end], va):
        mark = "  <-- MATCH" if (base + pe.get_rva_from_offset(off)) <= ins.address < (base + pe.get_rva_from_offset(off) + 15) else ""
        print("  0x%08X: %-10s %-25s %s" % (ins.address, ins.mnemonic, ins.op_str, mark))

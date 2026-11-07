import pefile

p = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32"
pe = pefile.PE(p)

found = False
for base_reloc in pe.DIRECTORY_ENTRY_BASERELOC:
    for entry in base_reloc.entries:
        if entry.rva == 0x20ABB8:
            print(f"Found reloc at RVA 0x{entry.rva:X}, type={entry.type}")
            # Locate file offset
            found = True
            break
    if found:
        break

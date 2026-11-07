import pefile, struct

p = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32"
pe = pefile.PE(p)

with open(p, "rb") as f:
    d = bytearray(f.read())

for base_reloc in pe.DIRECTORY_ENTRY_BASERELOC:
    page_rva = base_reloc.struct.VirtualAddress
    if page_rva == 0x20A000:
        print(f"Found page block 0x{page_rva:X}, size={base_reloc.struct.SizeOfBlock}")
        header_off = pe.get_offset_from_rva(pe.OPTIONAL_HEADER.DATA_DIRECTORY[5].VirtualAddress)
        # Find entry index
        for i, entry in enumerate(base_reloc.entries):
            if entry.rva == 0x20ABB8:
                print(f"  Entry index {i}: RVA=0x{entry.rva:X}, type={entry.type}")
                # The entries start at base_reloc.struct.get_field_absolute_offset(...)
                # Each base_reloc block is: DWORD VirtualAddress, DWORD SizeOfBlock, then WORD entries...
                block_file_off = pe.get_offset_from_rva(base_reloc.rva)
                entry_file_off = block_file_off + 8 + i * 2
                word = struct.unpack_from("<H", d, entry_file_off)[0]
                print(f"  Exact file offset: 0x{entry_file_off:X}, word=0x{word:04X}")
                break

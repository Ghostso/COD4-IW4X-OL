import struct, os, pefile

paths = [
    r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\CodolGameServer.dll"
]

target_off = 0x60F61E

for p in paths:
    with open(p, "rb") as f:
        data = bytearray(f.read())
    
    cur_word = struct.unpack_from("<H", data, target_off)[0]
    print(f"[{p}] Word @ 0x{target_off:X} = 0x{cur_word:04X}")
    assert cur_word == 0x3BB8, f"Expected 0x3BB8, got 0x{cur_word:04X}"
    
    # Change to 0x0000 (IMAGE_REL_BASED_ABSOLUTE / NOOP)
    struct.pack_into("<H", data, target_off, 0x0000)
    
    with open(p, "wb") as f:
        f.write(data)
    print(f"[{p}] Zeroed out reloc entry successfully!")

# Verify with pefile that 0x20ABB8 is no longer relocated
pe = pefile.PE(paths[0])
relocs = []
for base_reloc in pe.DIRECTORY_ENTRY_BASERELOC:
    for entry in base_reloc.entries:
        if entry.rva in [0x20ABB7, 0x20ABB8, 0x20ABB9, 0x20ABBA]:
            relocs.append((hex(entry.rva), entry.type))

print("\nOverlapping relocations now:", relocs)
assert len(relocs) == 0, "Relocations still present!"
print("PE relocation check PASSED: JMP offset will never be corrupted by Windows loader!")

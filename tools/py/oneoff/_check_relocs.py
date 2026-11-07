# -*- coding: utf-8 -*-
import pefile

p = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
pe = pefile.PE(p)
base = pe.OPTIONAL_HEADER.ImageBase

va_start = 0x1020ABAA
va_end = 0x1020ABBC

print(f"Checking relocations between 0x{va_start:X} and 0x{va_end:X}:")
found = []
if hasattr(pe, 'DIRECTORY_ENTRY_BASERELOC'):
    for base_reloc in pe.DIRECTORY_ENTRY_BASERELOC:
        for entry in base_reloc.entries:
            rva = entry.rva
            va = base + rva
            if va_start <= va <= va_end:
                found.append((hex(va), entry.type))

print("Found relocations:", found)
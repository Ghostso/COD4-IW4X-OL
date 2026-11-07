# -*- coding: utf-8 -*-
import pefile

p = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
pe = pefile.PE(p)
base = pe.OPTIONAL_HEADER.ImageBase

va = 0x1020ABAA
off = pe.get_offset_from_rva(va - base)
print(f"VA 0x{va:X} -> file offset 0x{off:X}")

with open(p, "rb") as f:
    d = f.read()

print("Bytes at 0x%X:" % off, d[off:off+18].hex())
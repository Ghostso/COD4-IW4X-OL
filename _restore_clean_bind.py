# -*- coding: utf-8 -*-
import os

p_curr = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
p_bak  = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32.bak"

with open(p_bak, "rb") as f: d_bak = bytearray(f.read())

# Keep the good patches:
# 1. 0x62B90: b801000000c3 (mov eax, 1; ret) -> bypass installDedicatedProcessPatches
# 2. 0x4D964: 0x0E659000 -> SizeOfImage for retail packed client
# 3. 0x209FB7: e95b0b0000 -> jump over the 82 prefix guards directly to RVA bindings
# 4. 0x6123C2: 0000 -> PE relocation fix

# In d_bak, apply ONLY these 4 good patches, keeping 0x1EE735 UNPATCHED (original failure log & return, NO HANG)
val_orig = 0x0E5D6000
val_patched = 0x0E659000
import struct
pos = d_bak.find(struct.pack("<I", val_orig))
if pos != -1:
    d_bak[pos:pos+4] = struct.pack("<I", val_patched)
    print(f"[+] Patched SizeOfImage at 0x{pos:X}")

# 0x62B90
d_bak[0x62B90:0x62B96] = bytes.fromhex("b801000000c3")
print("[+] Patched installDedicatedProcessPatches at 0x62B90")

# 0x209FB7
d_bak[0x209FB7:0x209FBC] = bytes.fromhex("e95b0b0000")
print("[+] Patched prefix jump at 0x209FB7")

# 0x6123C2
d_bak[0x6123C2:0x6123C4] = bytes.fromhex("0000")
print("[+] Patched reloc at 0x6123C2")

with open(p_curr, "wb") as f:
    f.write(d_bak)
print(f"[+] Written clean patched {p_curr} successfully!")
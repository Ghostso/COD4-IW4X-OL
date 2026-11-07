# -*- coding: utf-8 -*-
p = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
with open(p, "rb") as f: d = f.read()

import struct
val_orig = 0x0E5D6000
val_patched = 0x0E659000

pos_orig = d.find(struct.pack("<I", val_orig))
pos_patched = d.find(struct.pack("<I", val_patched))

print(f"0x0E5D6000 at: {hex(pos_orig) if pos_orig != -1 else 'Not found'}")
print(f"0x0E659000 at: {hex(pos_patched) if pos_patched != -1 else 'Not found'}")
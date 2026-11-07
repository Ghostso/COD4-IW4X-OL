# -*- coding: utf-8 -*-
p = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
with open(p, "rb") as f: d = f.read()

import struct
val_ts = 0x6096930A
pos_ts = 0
found = []
while True:
    pos_ts = d.find(struct.pack("<I", val_ts), pos_ts)
    if pos_ts == -1: break
    found.append(hex(pos_ts))
    pos_ts += 1

print(f"0x6096930A found at: {found}")
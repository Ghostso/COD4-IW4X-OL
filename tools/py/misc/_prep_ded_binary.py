# -*- coding: utf-8 -*-
import pefile, os

game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
ded_exe = os.path.join(game_dir, "codoMP_dedicated_server.exe")

with open(ded_exe, "rb") as f:
    d = bytearray(f.read())

old_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB30}}"
new_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}"

pos = d.find(old_name)
print(f"Found mutex at file offset: 0x{pos:X}")
if pos != -1:
    d[pos:pos+len(new_name)] = new_name
    with open(ded_exe, "wb") as f:
        f.write(d)
    print("Patched dedicated mutex name successfully!")
else:
    pos_new = d.find(new_name)
    if pos_new != -1:
        print("Mutex is already patched to dedicated name!")
    else:
        print("Mutex string not found!")
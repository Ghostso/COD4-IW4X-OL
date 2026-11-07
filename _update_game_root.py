# -*- coding: utf-8 -*-
path = r"REF_LOBBY_KIT\run_all.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Update GAME_ROOT to the user's only designated game root
old_root = 'GAME_ROOT = r"D:\\BaiduNetdiskDownload\\使命召唤OL\\run_codol_001\\sandbox_datafix_20260929"'
new_root = 'GAME_ROOT = r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL"'

if old_root in text:
    text = text.replace(old_root, new_root, 1)
    print("Updated GAME_ROOT in run_all.py to COD OL!")
else:
    print("Checking current GAME_ROOT in run_all.py...")
    import re
    m = re.search(r'GAME_ROOT\s*=\s*.*', text)
    if m:
        print("  Found:", m.group(0))

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
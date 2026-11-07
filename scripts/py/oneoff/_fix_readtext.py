# -*- coding: utf-8 -*-
path = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\launch_backend.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

new_text = text.replace(".read_text()", ".read_text(encoding='utf-8')")

with open(path, "w", encoding="utf-8") as f:
    f.write(new_text)

print("Fixed all bare read_text() to encoding='utf-8' successfully!")
import hashlib
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\build\bin\session_descriptor\mission_normal.bin"
b = open(p,"rb").read()
print("len:", len(b), "sha256:", hashlib.sha256(b).hexdigest())
# find printable ascii runs
import re
for m in re.finditer(rb"[\x20-\x7e]{3,}", b):
    print("  ascii@", m.start(), ":", m.group().decode())

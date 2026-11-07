# -*- coding: utf-8 -*-
import os, hashlib
wd=r"D:\BaiduNotdiskDownload\使命号嘥OL\E10_CONFIGSTRING_DISPATCH_001"

p=os.path.join(wd,"06_CLIENT_SERVER_CONFIGSTRING_MATRIX.md")
s=open(p,encoding="utf-8").read()
if "层属归更" not in s:
    s+="\n\n## 4. 层属归更（茧见 03 Χ 7）\n\n`0x04`/`0x06` @0100997 是 Gamestate(`0x03`) 内部子帧的头/尾；`0x06` @01022F8 是 Gamestate 顶层尾。\n"
    open(p,"w",encoding="utf-8",rewline="\n") write(s)
    print("appended 06")

names=[]
for root,dirs,files in os.walk(wd):
    for fn in sorted(files):
        if fn=="SHA256SUMS.txt": continue
        fp=os.path.join(root,fn)
        names.append((os.path.relpath(fp,wd).replace("\\","/"),fp))

def h(fp):
    hh=hashlib.sha256()
    with open(fp,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            hh.update(b)
    return hh.hexdigest()

lines=["# E-10 SHA256SUMS","# scope: E10_CONFIGSTRING_DISPATCH_001",""]
for rel,fp in sorted(names):
    lines.append(h(fp)+"  "+rel)
open(os.path.join(wd,"SHA256SUMS.txt"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print("entries",len(names))

import os, glob
files=[]
for dp,dn,fn in os.walk("TPFUI\\IIPSRes\\back"):
    for f in fn: files.append(os.path.join(dp,f))
print("back 下文件数:", len(files))
print("=== 大小分布 ===")
from collections import Counter
c=Counter(os.path.getsize(f) for f in files)
for sz,n in sorted(c.items())[:12]: print("   size=%-8d count=%d"%(sz,n))
print()
print("=== 前 8 个文件的头 16 字节 ===")
for f in sorted(files)[:8]:
    d=open(f,"rb").read(16)
    print("   %-55s %-8d %s" % (os.path.basename(f), os.path.getsize(f), d.hex()))
print()
print("=== 同名原始目录 COD OL\\IIPS\\TPFUI 对比 ===")
orig=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\TPFUI\IIPSRes\back\边玩边下\边玩边下底.png"
if os.path.isfile(orig):
    d=open(orig,"rb").read(16)
    print("   ORIG size=%d head=%s"%(os.path.getsize(orig), d.hex()))
else:
    print("   原始路径不存在")

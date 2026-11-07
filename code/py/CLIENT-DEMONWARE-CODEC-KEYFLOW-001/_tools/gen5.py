import os, hashlib
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-CODEC-KEYFLOW-001"
lines=[]
for f in sorted(x for x in os.listdir(root) if x.endswith(".md")):
    lines.append("%s  %s" % (hashlib.sha256(open(os.path.join(root,f),"rb").read()).hexdigest(), f))
dd=os.path.join(root,"_data")
for f in sorted(os.listdir(dd)):
    fp=os.path.join(dd,f)
    lines.append("%s  _data/%s" % (hashlib.sha256(open(fp,"rb").read()).hexdigest(), f))
open(os.path.join(root,"SHA256SUMS.txt"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print("\n".join(lines))

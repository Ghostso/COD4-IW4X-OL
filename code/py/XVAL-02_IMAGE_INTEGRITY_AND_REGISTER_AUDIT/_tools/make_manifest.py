import hashlib, os
OUT=r"D:\BaiduNetdiskDownload\使命召唤OL\XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT"
MAN=os.path.join(OUT,"SHA256SUMS.txt")
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20), b""): h.update(b)
    return h.hexdigest()
t=[]
for dp,dn,fs in os.walk(OUT):
    for fn in sorted(fs):
        p=os.path.join(dp,fn)
        if os.path.abspath(p)==os.path.abspath(MAN): continue
        t.append(p)
t.sort()
with open(MAN,"w",encoding="utf-8",newline="\n") as f:
    f.write("\n".join(f"{sha(p)}  {os.path.relpath(p,OUT).replace(chr(92),'/')}" for p in t)+"\n")
print("entries:",len(t))

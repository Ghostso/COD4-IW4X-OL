import os,re
root=r"D:\BaiduNetdiskDownload\使命召唤OL"
pats={
 "codec_mask_20": bytes.fromhex("f3421112 72f43241 09ae3f18 13eabc23".replace(" ",""))[:20],
 "pad_const": bytes.fromhex("411309ae3fa3bcf31872eabc093211cc124254f4"),
 "perm_bytes": bytes([7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]),
}
# fix mask
pats["codec_mask_20"]=bytes.fromhex("f342111272f4324109ae3f1813eabc2354bc09cc")
exts={".py",".cpp",".hpp",".h",".c",".cs",".txt",".md",".json"}
for name,pat in pats.items():
    print("====",name,pat.hex())
    n=0
    for dp,dn,fn in os.walk(root):
        if any(x in dp for x in ("__pycache__",)):
            continue
        for f in fn:
            if os.path.splitext(f)[1].lower() not in exts: continue
            p=os.path.join(dp,f)
            try:
                b=open(p,"rb").read()
            except Exception: continue
            if pat in b:
                print("   HIT",p); n+=1
                if n>15: break
        if n>15: break
    if n==0: print("   (no hits)")

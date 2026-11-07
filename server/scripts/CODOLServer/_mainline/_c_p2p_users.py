import os, pefile
# 谁（静态）导入 p2papp.dll / 谁字符串提到 GetP2PDownloadEx
for r in [r"COD OL", r"COD OL\IIPS", r"COD OL\Cross", r"COD OL\tqm"]:
    if not os.path.isdir(r): continue
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if not fn.lower().endswith((".exe",".dll")): continue
            p=os.path.join(dp,fn)
            try: d=open(p,"rb").read()
            except: continue
            for k in (b"p2papp", b"P2PApp", b"GetP2PDownloadEx", b"SetQQ", b"p2papi"):
                if k in d:
                    print("%-55s 含 %r"%(p,k))

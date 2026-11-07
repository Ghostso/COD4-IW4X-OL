import struct
p=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d=open(p,'rb').read()
# scan for 'mmbook accepted' and related strings in Base.dll
for s in [b"mmbook", b"mmbook accepted", b"mmstart", b"MM_RESERVE_CMD_REQUEST"]:
    idx=[]; st=0
    while True:
        i=d.find(s,st)
        if i<0: break
        idx.append(i); st=i+1
    print("%-24s count=%d  first=%s" % (s.decode(),len(idx), ["%X"%x for x in idx[:10]]))

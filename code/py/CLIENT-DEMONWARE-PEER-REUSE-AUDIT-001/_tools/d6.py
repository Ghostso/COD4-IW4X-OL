import sys,struct,re
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
d=im.d
# crypto strings across whole image
pats=[b"OpenSSL",b"openssl",b"EVP_",b"SHA1",b"sha1",b"HMAC",b"hmac",b"AES",b"aes",b"CBC",b"bcrypt",b"Bcrypt",b"CNG",b"crypto"]
for pat in pats:
    idx=[];i=d.find(pat)
    while i!=-1 and len(idx)<12:
        va=None
        for n,sv,vs,rp,rs,x in im.secs:
            if rp<=i<rp+rs: va=im.IB+sv+(i-rp); break
        idx.append((i,va));i=d.find(pat,i+1)
    print("%-9s hits=%d %s"%(pat.decode(),len(idx),[(hex(a) if a else None,hex(v) if v else None) for a,v in idx]))

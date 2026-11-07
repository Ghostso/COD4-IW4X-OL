import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
import re
for label,pat in [("CLIENTCHAL",b"CLIENTCHAL"),("BDDATA",b"BDDATA"),("HMAC mismatch",b"HMAC mismatch"),
                  ("Bad recv counter",b"Bad recv counter"),("Bad frame/payload size",b"Bad frame/payload size"),
                  ("HMAC calculation",b"HMAC calculation")]:
    hits=[]
    i=0
    while True:
        j=im.d.find(pat,i)
        if j<0: break
        for nm,va,vs,rp,rs,x in im.secs:
            if rp<=j<rp+rs: hits.append((nm,hex(va+(j-rp)))); break
        i=j+1
    print("%-22s %d hits %s"%(label,len(hits),hits[:8]))

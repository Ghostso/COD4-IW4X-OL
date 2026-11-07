import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
for pat in [b"CLIENTCHAL",b"BDDATA",b"CHALLENGE",b"challenge",b"CHAL",b"bddata",b"clientchal"]:
    cnt=im.d.count(pat); print("%-12s %d"%(pat.decode(),cnt))
print()
# search ASCII-ish variants
import re
for m in re.finditer(rb"[A-Za-z0-9_]{6,}", im.d):
    s=m.group()
    if b"CHAL" in s.upper() and len(s)<40:
        # print first 15
        pass
seen=set(); out=[]
for m in re.finditer(rb"[A-Za-z0-9_]{5,32}", im.d):
    s=m.group()
    if b"BDDATA" in s.upper() or b"CLIENTCHAL" in s.upper():
        if s not in seen: seen.add(s); out.append(s)
print("near-hits:",out[:20])
print()
# what protocol-ish strings exist?
for kw in [b"reliable",b"snapshot",b"gamestate",b"configstring",b"RELIABLE",b"SNAPSHOT"]:
    print("%-14s %d"%(kw.decode(), im.d.count(kw)))

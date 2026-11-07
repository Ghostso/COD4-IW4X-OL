import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C)
for pat in [b"CODOL2697_PROFILE_WIRE",b"challengeResponse",b"challengeResponse %d",b"CLIENTCHAL",b"BDDATA"]:
    print("client %-24s %d"%(pat.decode(),im.d.count(pat)))
print()
# client: search for session-ready signature 7F 00 00 01
import re
print("client '7f 00 00 01' occurrences:", len(re.findall(rb"\x7f\x00\x00\x01", im.d)))
print("server '7f 00 00 01' occurrences:", end=' ')
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im2=Img(S)
print(len(re.findall(rb"\x7f\x00\x00\x01", im2.d)))
print()
# client: does it have a clc 0..4 jump table / netchan XOR?
for kw in [b"CL_ParseServerMessage",b"clc_",b"CODOL2697",b"SV_Netchan"]:
    print("client %-22s %d"%(kw.decode(),im.d.count(kw)))

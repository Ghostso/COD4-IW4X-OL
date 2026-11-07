import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C)
print("=== 2.6.9.7 client: Demonware frame markers ===")
for pat in [b"bdLobby",b"dwLobby",b"dwRoom",b"dwStorage",b"bdCore",b"bdCommon",b"bdLobbyService",b"AB\x85",b"\x00AB"]:
    print("  %-16s %d"%(pat.decode('latin1','replace'), im.d.count(pat)))
print()
print("=== 2697 client: is it IW4-lineage? ===")
for pat in [b"iw4\\code_source", b"com_memory.cpp", b"codoMP_client_shipRetail.pdb", b"IWffs100", b"IW4"]:
    print("  %-30s %d"%(pat.decode('latin1','replace'), im.d.count(pat)))

import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
base=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697"
for f in ["client_room2697.dll","client_native_loopback.dll"]:
    p=base+"\\"+f
    im=Img(p)
    print("=== %s  IB=%08X SizeOfImage=%08X ==="%(f,im.IB,im.pe.OPTIONAL_HEADER.SizeOfImage))
    for pat in [b"CLIENTCHAL",b"BDDATA",b"HMAC mismatch",b"Bad recv counter",b"challengeResponse",b"HMAC",b"0x81"]:
        print("   %-18s %d"%(pat.decode(),im.d.count(pat)))

import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
# Does 2697 client contain the s1x/reference code at the cited addresses?
print("=== 2697 client at addresses cited by the DW3 peer docs ===")
for va,label in [(0x9CE310,"bdLobbyConnection::getMessageToDispatch"),(0xA58F00,"Auth3 fn"),(0x6C7C90,"ticket parse"),(0x6C8BC0,"ticket"),(0x79C0F0,"ticket")]:
    r=va-IB
    sec=im.sec(r) if 0<=r<0xDC14000 else None
    o=im.off(r) if sec else None
    txt=None
    if o is not None: txt=bytes(im.dis(r,16)[0].bytes).hex() if im.dis(r,16) else None
    print("  VA %08X RVA %07X sec=%-8s first16=%s"%(va,r,sec,txt))
print()
# The decisive test: does the 2697 client contain the 3DES/AES + DEADBEEF magic + bdLobby frame chain?
print("=== 2697 client: DW lobby markers ===")
for pat in [bytes.fromhex('efbeadde'), b'bdLobby', b'dwLobby', b'bdLobbyConnection', b'getMessageToDispatch', b'CLIENTCHAL', b'BDDATA']:
    print("  %-24s %d"%(pat.decode('latin1','replace'), im.d.count(pat)))

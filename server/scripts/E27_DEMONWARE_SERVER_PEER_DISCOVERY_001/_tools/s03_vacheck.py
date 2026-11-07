import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
# lobby cites client VAs: 0x9CE310, 0x7C6DA60, 0x9BAFD0, 0x9BA070, 0x703A00, 0x7039A0, 0x711CD6, 0x6FDAC4, 0xA2E880
for va,label in [(0x9CE310,"bdLobbyConnection::getMessageToDispatch"),(0x9BAFD0,"reader memcpy"),
                 (0x9BA070,"readBlob"),(0x703A00,"dwLogOnAccount_DecodeString"),(0x7039A0,"dwLogOnAccount_EncodeString"),
                 (0x711CD6,"chat log site"),(0x6FDAC4,"getChannelMembers completion"),(0xA2E880,"bdBase64::decode"),
                 (0xA2E790,"base64 char->6bit"),(0x7C6DA60,"calculateInitialVector")]:
    r=va-IB
    sec=im.sec(r) if 0<=r<0xDC14000 else None
    print("  VA %08X RVA %07X sec=%s"%(va,r,sec))

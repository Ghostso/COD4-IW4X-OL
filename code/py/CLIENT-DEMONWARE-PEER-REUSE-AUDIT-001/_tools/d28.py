import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
old=[(0x9CE310,"dw_wire bdLobbyConnection::getMessageToDispatch"),
     (0x7C6DA60,"calculateInitialVector"),
     (0x9BAFD0,"reader memcpy"),(0x9BA070,"readBlob"),
     (0x703A00,"dwLogOnAccount_DecodeString"),(0x7039A0,"dwLogOnAccount_EncodeString"),
     (0xA2E880,"bdBase64::decode"),(0xA2E790,"base64 char->6bit"),
     (0x711CD6,"chat log site"),(0x6FDAC4,"getChannelMembers completion")]
print("ImageBase",hex(IB),"SizeOfImage",hex(im.pe.OPTIONAL_HEADER.SizeOfImage))
for va,lab in old:
    r=va-IB; sec=im.sec(r); b=im.rd(va,16) if sec else None
    print("  %08X RVA %08X sec=%-8s bytes=%s   %s"%(va,r,sec,(b.hex(" ") if b else "OOB/UNMAPPED"),lab))

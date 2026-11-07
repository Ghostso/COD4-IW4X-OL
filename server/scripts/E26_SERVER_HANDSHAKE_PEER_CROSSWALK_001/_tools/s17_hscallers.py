import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
n,va,vs,rp,rs,x=[s for s in im.secs if s[0]==".text"][0]
data=im.d[rp:rp+rs]
def callers(tva,opc=(0xe8,0xe9)):
    out=[]
    for i in range(len(data)-5):
        if data[i] in opc:
            rel=struct.unpack_from('<i',data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),hex(data[i])))
    return out
for nm,rva in [("_CODOL_HandshakeInit",0x982A3),("_CODOL_HandshakeClear",0x9828D),
               ("_CODOL_HandshakeCookie",0x9857B),("_CODOL_WriteChallengeResponse",0x97592),
               ("_SV_ExecuteClientMessage",0x72DBB),("_SV_Netchan_Transmit",0x856B6),
               ("_SV_ConnectionlessPacket",0x8487F),("_SV_DirectConnect",0x6F2C0),
               ("_SV_ReadPackets",0x6E2D5)]:
    print("%-28s callers: %s"%(nm,callers(IB+rva)))
print()
print("=== clc_strings at VA 0x7B3800 ===")
import re
b=im.bytes(0x7B3800-IB,0x60)
print(b)
for m in re.finditer(rb"[ -~]{3,}", b): print("  ",m.group())

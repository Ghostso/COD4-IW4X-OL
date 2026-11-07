import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("recovered ImageBase",hex(im.IB),"SizeOfImage",hex(im.pe.OPTIONAL_HEADER.SizeOfImage))
for rva in (0x6AB310,0x6AB8C5,0x6AB907,0x5CE310,0x9CE310,0x786DA60,0x386DA60,0x5BAFD0,0x303A00,0x62E880):
    va=im.IB+rva; sec=im.sec(rva); b=im.bytes(rva,16)
    print("  RVA %08X VA %08X sec=%-8s %s"%(rva,va,sec,(b.hex(" ") if b else "OOB")))

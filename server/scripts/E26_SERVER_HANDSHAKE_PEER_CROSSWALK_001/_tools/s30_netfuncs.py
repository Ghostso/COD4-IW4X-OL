import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_data\out_netfuncs.txt","w",encoding="utf-8")
def d(rva,n,tag):
    OUT.write("="*76+"\n%s RVA %06X VA %08X\n"%(tag,rva,IB+rva))
    o=im.off(rva)
    if o is None: OUT.write("NO_RAW\n"); return
    for i in im.dis(rva,n): OUT.write("%06X %-22s %s %s\n"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
for rva,n,tag in [(0x9A2A6,0x88,"_CODOL_NetworkInit"),
                  (0x9A32E,0x6D,"_CODOL_NetworkAdmission"),
                  (0x9A3A5,0x55,"_CODOL_NetworkAuthenticated"),
                  (0x9A3FA,0x78,"_CODOL_NetworkSessionReady"),
                  (0x9A472,0xDA,"_CODOL_NetworkSend"),
                  (0x9A15D,0x23,"_CODOL_NetworkReset")]:
    d(rva,n,tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_data\out_netfuncs.txt",encoding="utf-8").read())

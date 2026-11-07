import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
# string at VA 0x7BCCCA
r=0x7BCCCA-im.IB
b=im.bytes(r,64)
print("VA 0x7BCCCA sec=%s raw=%s"%(im.sec(r), b[:48] if b else None))
print("ascii:", (b.split(b'\0')[0].decode('latin1') if b else None))
# search for CLIENTCHAL/BDDATA inside .rdata/.data as split
for pat in [b'CLIENT',b'CHAL',b'BDDATA',b'BD\x00',b'clientchal']:
    print(pat, im.d.count(pat))

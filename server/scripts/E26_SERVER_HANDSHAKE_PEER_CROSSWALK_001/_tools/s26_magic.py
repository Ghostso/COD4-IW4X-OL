import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
for va in (0x7B9812,0x7B9829,0x7B9810,0x7BCCCA,0x7B9800):
    b=im.rd(va,48); txt=(b.split(b'\0')[0] if b else b'')
    print("  VA %08X sec=%s : %r"%(va,im.sec(va-IB),txt))
print()
print("=== Netchan_Decode magic check 0x4A/0x4B ===")
for i in im.dis(0x485619,0x20): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))

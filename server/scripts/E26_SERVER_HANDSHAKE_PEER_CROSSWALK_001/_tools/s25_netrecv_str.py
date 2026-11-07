import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
# all string literals referenced inside _CODOL_NetworkReceive (push imm32 in .rdata)
n,va,vs,rp,rs,x=[s for s in im.secs if s[0]==".text"][0]
print("=== immediates pushed in _CODOL_NetworkReceive that point into .rdata/.data ===")
for i in im.dis(0x9A54C,0x10C0):
    s=i.op_str
    if i.mnemonic=="push" and s.startswith("0x"):
        v=int(s,16)
        if 0x400000<=v<IB+im.pe.OPTIONAL_HEADER.SizeOfImage:
            sec=im.sec(v-IB)
            b=im.rd(v,40)
            txt=(b.split(b'\0')[0] if b else b'')
            printable=all(32<=c<127 for c in txt) and len(txt)>=3
            print("  %06X push %08X sec=%s %s"%(i.address-IB,v,sec, repr(txt) if printable else ''))

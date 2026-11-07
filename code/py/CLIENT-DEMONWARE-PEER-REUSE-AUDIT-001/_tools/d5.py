import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
# find true function start for label region: walk back from 0xAAB8C5 until int3 padding after ret
d=im.d
pos=0xAAB8C5-0x400000
# find nearest preceding 0xCC run followed by prologue
starts=[]
i=pos
while i>pos-0x1200:
    if d[i]==0x55 and d[i+1]==0x8b and d[i+2]==0xec:
        starts.append(i+0x400000)
    i-=1
print("prologue candidates:",[hex(s) for s in starts[:10]])
# disassemble from earliest plausible that has no int3 gap? just show 0xAAB600..0xAAA910 region around secret usage at 0xaab760..0xaab930
for i in im.dis(0xAAB6D0-0x400000, 0x2A0):
    print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))

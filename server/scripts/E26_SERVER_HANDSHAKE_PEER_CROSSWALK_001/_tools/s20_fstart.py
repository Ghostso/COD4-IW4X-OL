import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
def fstart(rva):
    j=rva
    while j>0x1000:
        o=im.off(j)
        if im.d[o]==0x55 and im.d[o+1]==0x89 and im.d[o+2]==0xe5: return j
        j-=1
    return rva
for a in (0x9B027,0x9B477,0x9B1B9):
    st=fstart(a); print("call site %06X -> func start %06X (offset +0x%X)"%(a,st,a-st))
print()
n,va,vs,rp,rs,x=[s for s in im.secs if s[0]==".text"][0]
data=im.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,0xe9):
            rel=struct.unpack_from('<i',data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),hex(data[i])))
    return out
for st in (fstart(0x9B027),):
    print("callers of %06X:"%st, callers(IB+st))
# also list all symbols near 0x9Axxx-0x9Bxxx
import json
j=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json",encoding='utf-8'))
S2=sorted([s for s in j['symbols'] if isinstance(s,dict) and 0x99000<=s['rva']<=0x9C000], key=lambda s:s['rva'])
for s in S2: print("   %08X %s"%(s['rva'],s['name']))

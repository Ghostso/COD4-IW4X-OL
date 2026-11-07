import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
BASE=0x400000; END=0x400000+0x0E659000
txt=data[BASE-LO:END-LO]
def find(pat):
    out=[];i=0
    while True:
        i=txt.find(pat,i)
        if i<0:break
        out.append(BASE+i);i+=1
    return out
# 8-bit immediate compares against each code, any of several registers
groups={}
for code in (0x81,0x83,0x84,0x85):
    s=set()
    for pat in (bytes([0x3C,code]), bytes([0x80,0xF9,code]), bytes([0x80,0xFA,code]),
                bytes([0x80,0xFB,code]), bytes([0x80,0xFE,code]), bytes([0x80,0xFF,code])):
        s.update(find(pat))
    groups[code]=sorted(s)
# cluster: window where all four appear within W bytes
W=0x600
res=[]
for a in groups[0x81]:
    win=[a,a+W]
    cov=[c for c in groups if any(win[0]<=x<=win[1] for x in groups[c])]
    if len(cov)>=4:
        res.append((a,cov))
# merge overlapping
merged=[]
for a,cov in res:
    if merged and a-merged[-1][0]<=W: continue
    merged.append((a,cov))
print("clusters containing all 4 codes within 0x%X bytes:"%W)
for a,cov in merged[:20]:
    print("  start=0x%08X  codes=%s"% (a, sorted(hex(c) for c in cov)))

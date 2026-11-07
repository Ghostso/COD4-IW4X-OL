import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
j=0x6AA465
while j>0x1000 and img.d[img.off(j)-1]!=0xcc: j-=1
print("func start:",hex(j))
for i in img.dis(j,0x6AA4A8-j): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== all callers of enqueue 0xDF806F2 (all sections) ===")
for nm,sva,svs,srp,srs,sx in img.secs:
    if srs==0: continue
    blob=img.d[srp:srp+srs]
    for i in range(len(blob)-5):
        if blob[i]==0xe8:
            rel=struct.unpack_from('<i',blob,i+1)[0]
            if ((IB+sva+i+5+rel)&0xffffffff)==0xDF806F2: print("  %s %06X"%(nm,sva+i))

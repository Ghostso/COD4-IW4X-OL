import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# 1) does any function in the 0x6A9000..0x6AD000 (session) range reference the send/sendto IAT?
targets={0xBAE4C8:"send",0xBAE504:"sendto"}
print("=== send/sendto IAT refs inside session range 0x6A9000..0x6AD000 ===")
for i in img.dis(0x6A9000,0x6AD000-0x6A9000):
    s=i.op_str.lower()
    if "0xbae4c8" in s or "0xbae504" in s:
        print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print("  (none printed => no direct send/sendto ref in session range)")
print()
# 2) any branch/call in the session range to the send-wrapper addresses?
wrap={0x775A00:"wsock-send-obj",0x775A22+0-0x22+0x22:"",0x775A22:"send-wrapper",0x775A80:"recv-wrapper",0x775AA4:"sendto-wrapper",0x6028F0:"send@6028F0",0x6B4C94:"sendto@6B4C94"}
print("=== direct rel32 calls from session range to send wrappers ===")
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
want={0x775A00,0x775A22,0x775A80,0x775AA4,0x6028F0,0x6B4C94,0x784E5F,0x787FE5}
for i in range(0x6A9000-va, 0x6AD000-va):
    if data[i]==0xe8:
        rel=struct.unpack_from("<i",data,i+1)[0]
        tr=(va+i+5+rel)&0xffffffff
        if tr in want: print("  %06X -> RVA %06X"%(va+i,tr))
print("  (none printed => no direct call to send wrappers from session range)")

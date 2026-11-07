import sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
# verify: scan the DLL image for a *decrypt* schedule too, and for EVP-style
import aes_schedule_hunt as A
print('RCON',A.RCON[:4])
# quick self-test of expand_key
k=bytes.fromhex('2b7e151628aed2a6abf7158809cf4f3c')
s=A.expand_key(k)
print('expand len',len(s),'w4',s[16:20].hex())

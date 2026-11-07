import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
print("=== pump head: 0x6AA7B0..0x6AA7F0 (uses +0x628) ===")
for i in img.dis(0x6AA7B0,0x45): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0x6AAE00..0x6AAE40 (2nd pump call 0x6AAE13) ===")
for i in img.dis(0x6AAE00,0x50): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
# the pump's +0x628 indirect: check it is called with no args (virtual call on transport)
# 0x6AA7B7 mov ecx,[esi+0x628]; test; mov eax,[ecx]; mov edx,[eax]; call edx  => slot0
print("  => pump calls transport->slot0() (vtable[0]) as a 'reset/flush' hook")

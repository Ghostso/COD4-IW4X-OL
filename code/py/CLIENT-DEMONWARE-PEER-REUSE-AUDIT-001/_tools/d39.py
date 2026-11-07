import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
# Determine A87830 read/write roles used after expandKey by examining param order at call sites
# Site1 0xAAB8CF (CLIENTCHAL): push 0x10 [ebp-0x38] ; push 0xA("CLIENTCHAL"); push [ebp-0x4c](secret,20); push &[ebp-0x4c]; push &[ebp-0x4c]+? ; call
for a in (0xAAB8A0,0xAAB8C2,0xAAB8C9,0xAAB8CC,0xAAB8CE,0xAAB8F6,0xAAB904,0xAAB90B,0xAAB911):
    pass
print("expandKey prologue/args:")
for i in im.dis(0xAA9CE0-0x400000, 0x40):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))

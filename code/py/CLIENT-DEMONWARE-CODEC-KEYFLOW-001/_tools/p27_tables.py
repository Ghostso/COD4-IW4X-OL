import struct, sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("decoded tables (client):")
orderA=[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]
print(" A:",orderA)
print(" B:[19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]")
print("C# A: 7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15")
print("C# B: 19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11")
print("perm A identical:", orderA==[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15])
print("perm B identical (with 16 at idx13):", [19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]==[19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11])
# verify the two "fill" instructions
print()
print("0xAA8C12:", im.rd(0xAA8C12,6).hex(" "), " <- mov [ebp-0x34],edx (edx=0x10=16)")
print("0xAA8D95:", im.rd(0xAA8D95,4).hex(" "), " <- mov [ebp-0x58],edx (edx=9)")

import struct, sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
print("C# CONST_A words ->", [hex(x) for x in (2919830337,4089226047,3169481240,3423678985,4099162642)])
print("C# CONST_B words ->", [hex(x) for x in (2866684544,4095810571,938409728,3457192487,557642922)])
a=b"".join(struct.pack("<I",x) for x in (2919830337,4089226047,3169481240,3423678985,4099162642))
b=b"".join(struct.pack("<I",x) for x in (2866684544,4095810571,938409728,3457192487,557642922))
print("C# CONST_A bytes:", a.hex())
print("2697 CONST_A bytes:", "411309ae3fa3bcf31872eabc093211cc124254f4")
print("match A:", a.hex()=="411309ae3fa3bcf31872eabc093211cc124254f4")
print("C# CONST_B bytes:", b.hex())
print("2697 CONST_B bytes:", "8022deaa0b1c21f400ffee37279210ceaaf43c21")
print("match B:", b.hex()=="8022deaa0b1c21f400ffee37279210ceaaf43c21")
im=Img()
print()
print("codec B table writes 0xAA8C3C-0xAA8CC2 verbatim:")
for i in im.dis(0xAA8C3C-0x400000, 0x86):
    print("  %08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))

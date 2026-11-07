import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
def mask(const_hex, perm):
    C=bytes.fromhex(const_hex); return bytes(C[perm[i]] for i in range(len(perm)))
A=mask("411309ae3fa3bcf31872eabc093211cc124254f4",[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15])
B=mask("8022deaa0b1c21f400ffee37279210ceaaf43c21",[19,18,9,4,17,1,10,8,13,2,15,3,12,5,7,0,14,6,11])
print("codec A effective XOR mask:", A.hex())
print("codec B effective XOR mask:", B.hex())
print("A len",len(A),"B len",len(B))
# net effect: store then load with same mask
import os
x=os.urandom(20)
print("codecA store->load identity:", bytes(a^b^c for a,b,c in zip(A,A,x))==x)
print("codecA(PERM order) = ", [7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15])
print("codecB(PERM order) = ", [19,18,9,4,17,1,10,8,13,2,15,3,12,5,7,0,14,6,11])

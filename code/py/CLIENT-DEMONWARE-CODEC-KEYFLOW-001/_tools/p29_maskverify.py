import struct
CA=bytes.fromhex("411309ae3fa3bcf31872eabc093211cc124254f4")
CB=bytes.fromhex("8022deaa0b1c21f400ffee37279210ceaaf43c21")
PA=[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]
PB=[19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]
print("len CA",len(CA),"len CB",len(CB),"len PA",len(PA),"len PB",len(PB))
MA=bytes(CA[PA[i]] for i in range(20))
MB=bytes(CB[PB[i]] for i in range(20))
print("M_A",MA.hex())
print("M_B",MB.hex())
# C# DecodeKey semantics: out[j] = src[j] ^ words_flattened[indices[j]]
import itertools
wordsA=[2919830337,4089226047,3169481240,3423678985,4099162642]
wordsB=[2866684544,4095810571,938409728,3457192487,557642922]
flatA=b"".join(struct.pack("<I",w) for w in wordsA)
flatB=b"".join(struct.pack("<I",w) for w in wordsB)
csA=bytes(flatA[PA[i]] for i in range(20))
csB=bytes(flatB[PB[i]] for i in range(20))
print("C# decoded A",csA.hex(),"match client M_A:",csA==MA)
print("C# decoded B",csB.hex(),"match client M_B:",csB==MB)
# net identity check
import os
x=os.urandom(20)
store=bytes(a^b for a,b in zip(x,MA)); load=bytes(a^b for a,b in zip(store,MA))
print("client A store->load identity:",load==x)
storeB=bytes(a^b for a,b in zip(x,MB)); loadB=bytes(a^b for a,b in zip(storeB,MB))
print("client B store->load identity:",loadB==x)

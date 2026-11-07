import pathlib,struct
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
for a,b in [(0xCA8740,0xCA8790),(0xCA83C0,0xCA8420),(0xCA8460,0xCA84C0),(0xCA84C0,0xCA8520)]:
 print('\n%08X..%08X'%(a,b))
 for va in range(a,b,4):print('%08X %08X'%(va,rd(va)))

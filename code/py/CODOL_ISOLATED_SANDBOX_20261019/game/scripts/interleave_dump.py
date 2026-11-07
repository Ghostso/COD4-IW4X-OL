import pathlib,struct
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
for a,b in [(0xCA8C80,0xCA8D80),(0xCA8760,0xCA8800)]:
 print('\n%08X..%08X'%(a,b))
 for va in range(a,b,4):print('%08X %08X'%(va,rd(va)))

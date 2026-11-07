import pathlib,struct
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
for va in range(0xCA84B0,0xCA8568,4):
 v=rd(va); print('%08X %08X'%(va,v))

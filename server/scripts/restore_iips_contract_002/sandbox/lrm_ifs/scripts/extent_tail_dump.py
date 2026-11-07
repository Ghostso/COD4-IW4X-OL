import struct, pathlib
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; raw0=0x594000; va0=0x8A8000
def rd(va): return struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
for a,b in [(0xCA9300,0xCA9460),(0xCA9350,0xCA93F0),(0xCA87F0,0xCA8860)]:
 print('\n%08X..%08X'%(a,b))
 for va in range(a,b,4): print('%08X %08X'%(va,rd(va)))

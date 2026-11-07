import struct, pathlib, collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; raw0=0x594000; va0=0x8A8000
def rd(va): return struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
# examine around likely natural boundaries in a tight window
for va in range(0x00CA8000,0x00CA8800,4):
    v=rd(va)
    if (va & 0x3f)==0:
        print('\n%08X:'%va,end=' ')
    print('%08X'%v,end=' ')
print()

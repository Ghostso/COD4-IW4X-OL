import struct
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe_off=0x400; va_text=0x10001000
# .idata2 at raw 0xaf7c00 rva 0xb02000
base_rva=0xb02000; raw=0xaf7c00
def rva2off(r): return raw+(r-base_rva)
print('--- idata2 head 0xb02000..0xb02380 ---')
for i in range(0,0x380,16):
    b=d[raw+i:raw+i+16]
    print('%#010x  %s  %s'%(0x10000000+base_rva+i,b.hex(' '),''.join(chr(c) if 32<=c<127 else '.' for c in b)))

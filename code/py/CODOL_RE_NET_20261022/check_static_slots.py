p=r'COD OL\codoMP_client_shipRetail.exe'
d=open(p,'rb').read()
def rva2off(r):
    secs=[(0x1000,0x1000,0x593000),(0x8a8000,0x594000,0x16e000),(0xa16000,0x702000,0x62000),(0xe5c8000,0x764000,0x1000),(0xe5c9000,0x765000,0xa000),(0xe5d3000,0x76f000,0x2000),(0xe5d7000,0x771000,0x6000)]
    for va,raw,sz in secs:
        if va<=r<va+sz: return raw+(r-va)
for rva in [0xCA8534,0xCA8538,0xCA855C]:
    o=rva2off(rva)
    print('%#x -> file offset %s  bytes=%s'%(rva,hex(o) if o else 'None', d[o:o+16].hex(' ') if o else 'OUT_OF_FILE'))

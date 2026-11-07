p=r'COD OL\codoMP_client_shipRetail.exe'
d=open(p,'rb').read()
def off(rva):
    secs=[(0x1000,0x1000,0x593000),(0x8a8000,0x594000,0x16e000),(0xa16000,0x702000,0x62000),(0xe5c8000,0x764000,0x1000),(0xe5c9000,0x765000,0xa000),(0xe5d3000,0x76f000,0x2000),(0xe5d7000,0x771000,0x6000)]
    for va,raw,sz in secs:
        if va<=rva<va+sz: return raw+(rva-va)
for rva,label in [(0xE5DC65D,'OFT/thunks'),(0xE5DC66D,'DLL name'),(0xE5DC665,'IAT')]:
    o=off(rva); print(label,hex(rva),'->',hex(o),d[o:o+40].hex(' '),repr(d[o:o+40]))

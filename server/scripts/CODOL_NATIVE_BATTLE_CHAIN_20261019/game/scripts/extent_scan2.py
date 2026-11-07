import struct, pathlib, collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes()
IB=0x400000; SOI=0x0E659000
# section #1 exact raw extent
rva0=0x8A8000; raw0=0x594000; rawsz=0x16E000; vsz=0x16DA70
lo=IB+rva0; hi=IB+rva0+rawsz
def rd(va):
    off=raw0+va-lo
    return struct.unpack_from('<I',D,off)[0] if raw0<=off<=raw0+rawsz-4 else None
def cls(v):
    if v is None:return 'O'
    if v==0:return 'Z'
    if IB<=v<IB+SOI:return 'P'
    if 0x80000000<=v<=0x8fffffff:return 'S'
    if 1<=v<=0xFFFFFF:return 'N'
    return 'X'
vals=[rd(va) for va in range(lo,hi,4)]
print('section1 VA=%08X..%08X rawsz=%X'%(lo,hi,rawsz))
# zero runs >=16 bytes
zr=[]; s=None
for i,v in enumerate(vals):
    if v==0 and s is None:s=i
    if (v!=0 or i==len(vals)-1) and s is not None:
        e=i-1 if v!=0 else i
        if e-s+1>=4:zr.append((lo+4*s,lo+4*e,e-s+1))
        s=None
print('zero runs>=4 dwords:',len(zr))
for a,b,n in zr[:100]: print('  %08X..%08X n=%d'%(a,b,n))
# category runs >=8 dwords
print('\ncategory runs>=8 dwords:')
s=0
for i in range(1,len(vals)+1):
    if i==len(vals) or cls(vals[i])!=cls(vals[s]):
        if i-s>=8: print('  %08X..%08X %s n=%d first=%08X last=%08X'%(lo+4*s,lo+4*(i-1),cls(vals[s]),i-s,vals[s] if vals[s] is not None else 0,vals[i-1] if vals[i-1] is not None else 0))
        s=i
print('\nblock summaries 0x400:')
for va in range(lo,hi,0x400):
    cc=collections.Counter(cls(rd(x)) for x in range(va,min(va+0x400,hi),4))
    print('  %08X P=%3d Z=%3d S=%3d N=%2d X=%3d'%(va,cc['P'],cc['Z'],cc['S'],cc['N'],cc['X']))

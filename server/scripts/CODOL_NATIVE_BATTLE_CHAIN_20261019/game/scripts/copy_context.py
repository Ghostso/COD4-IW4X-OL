import pathlib,struct
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
secs=[(0,'.tp3',0x1000,0x8A689A,0x1000,0x593000),(1,'.tp3',0x8A8000,0x16DA70,0x594000,0x16E000),(2,'.tp3',0xA16000,0xDBB1CC0,0x702000,0x62000),(3,'.tp3',0xE5C8000,0x31,0x764000,0x1000),(4,'.tp3',0xE5C9000,0x9228,0x765000,0xA000),(5,'.tvm0',0xE5D3000,0x4000,0x76F000,0x2000),(6,'.tp3',0xE5D7000,0x82000,0x771000,0x6000)]
def loc(o):
 for i,n,rva,vs,rp,rs in secs:
  if rp<=o<rp+rs:return '%s#%d VA=%08X RVA=%08X +%X'%(n,i,IB+rva+o-rp,rva+o-rp,o-rp)
 return '?'
for o in [0x594000,0x6FE944,0x594780,0x594D10]:print(hex(o),loc(o))
# compare entire 0x768-byte callable region to copy
a=D[0x594000:0x594768]; b=D[0x6FE944:0x6FE944+len(a)]
print('copy exact',a==b,'diffs',sum(x!=y for x,y in zip(a,b)),'of',len(a))
# match common prefix/suffix by per-dword identity
for n in [8,16,32,64,128,256,471,512]:
 a=D[0x594000:0x594000+4*n]; b=D[0x6FE944:0x6FE944+4*n]
 eq=sum(struct.unpack_from('<I',a,4*i)==struct.unpack_from('<I',b,4*i) for i in range(n))
 print('n',n,'equal dwords',eq)

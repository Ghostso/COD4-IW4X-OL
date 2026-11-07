import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
# boundary located by last direct reference in raw table area
last=max(0xCA875C,0xCA8374,0xCA855C)
print('last exact ref slot',hex(last))
# counts before/after boundary
refs=[]
for off in range(len(D)-6):
 if D[off]==0xFF and D[off+1] in (0x15,0x25):
  v=struct.unpack_from('<I',D,off+2)[0]
  if 0xCA8000<=v<0xCA9400: refs.append(v)
print('refs',len(refs),'maxslot',hex(max(refs)),'unique',len(set(refs)))
print('after 0xCA875C',sum(v>0xCA875C for v in refs),'after 0xCA876C',sum(v>=0xCA876C for v in refs))
# exact dword occurrences of addresses around candidate boundaries
for va in [0xCA8758,0xCA875C,0xCA8760,0xCA8764,0xCA8768,0xCA876C,0xCA8780]:
 pat=struct.pack('<I',va); n=D.count(pat)
 print('%08X exact_dword=%d value=%08X'%(va,n,rd(va)))

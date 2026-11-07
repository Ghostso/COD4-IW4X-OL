import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
ffset=set(); movset=set(); refs=[]
for off in range(len(D)-6):
 if D[off]==0xFF and D[off+1] in (0x15,0x25):
  v=struct.unpack_from('<I',D,off+2)[0]
  if 0xCA8000<=v<0xCA9400: ffset.add(v); refs.append(('ff%02x'%D[off+1],off,v))
 elif D[off] in range(0x8B,0x90) and (D[off+1]&0xC7)==0x05:
  v=struct.unpack_from('<I',D,off+2)[0]
  if 0xCA8000<=v<0xCA9400: movset.add(v); refs.append(('mov',off,v))
print('ff slots',len(ffset),'mov slots',len(movset),'union',len(ffset|movset),'mov-only',sorted(hex(x) for x in movset-ffset))
print('ff-only',len(ffset-movset),'both',len(ffset&movset))
# only within the user 512-dword range
print('within512 ff',len([x for x in ffset if x<0xCA8800]),'mov',len([x for x in movset if x<0xCA8800]),'union',len([x for x in ffset|movset if x<0xCA8800]))
# unique exact 5-byte/6-byte FF pattern stats also detect unaligned overlaps
print('mov-only in 512',sorted(hex(x) for x in movset-ffset if x<0xCA8800))
# slot gaps / used range
used=sorted(ffset|movset)
print('min',hex(used[0]),'max',hex(used[-1]))
print('unused table dwords <=0xCA875C count',sum(x not in ffset for x in range(0xCA8000,0xCA8760,4)))
# exact occurrence vs actual bytes
for s in sorted(ffset)[:5]: print('slot',hex(s),'dword occurrences',D.count(struct.pack('<I',s)))

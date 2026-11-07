import pathlib,struct
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
def find_seq(vals):
 b=b''.join(struct.pack('<I',v) for v in vals); out=[]; p=D.find(b)
 while p>=0: out.append(p);p=D.find(b,p+1)
 return out
seqs={
 'start16':[rd(0xCA8000+4*i) for i in range(16)],
 'region_c95_16':[rd(0xCA8780+4*i) for i in range(16)],
 'region_c98_16':[rd(0xCA8D10+4*i) for i in range(16)],
 'ca876c_5':[rd(0xCA876C+4*i) for i in range(5)]}
for k,v in seqs.items():
 rs=find_seq(v); print(k,['0x%X'%x for x in rs])
# find contiguous 8-dword runs in file that match table sequence at constant delta; report exact plus +-0x1000/0x10000 shifts
for k,v in seqs.items():
 for delta in [0,0x1000,-0x1000,0x10000,-0x10000,0x600000,-0x600000]:
  w=[x+delta for x in v]; rs=find_seq(w)
  if rs:print('delta',k,hex(delta),['0x%X'%x for x in rs])
# count individual target values occurrences outside table
vals=[rd(0xCA8000+4*i) for i in range(0x768//4)]
print('\nvalue occurrence stats outside table')
for v in sorted(set(vals)):
 if v and 0xA13000<=v<0xA15600:
  p=struct.pack('<I',v); n=D.count(p)
  if n>1: print('%08X dword_occ=%d'%(v,n))

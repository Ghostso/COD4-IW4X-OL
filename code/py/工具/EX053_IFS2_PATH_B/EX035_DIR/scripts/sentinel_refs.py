import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
# all sentinel-valued slots and their addressing style
refs=[]
for off in range(len(D)-6):
 if D[off]==0xFF and D[off+1] in (0x15,0x25):
  va=struct.unpack_from('<I',D,off+2)[0]; refs.append((off,va,D[off+1]))
# map file offset to rva
secs=[(0x1000,0x593000,0x1000),(0x8A8000,0x16E000,0x594000),(0xA16000,0x62000,0x702000),(0xE5C8000,0x1000,0x764000),(0xE5C9000,0xA000,0x765000),(0xE5D3000,0x2000,0x76F000),(0xE5D7000,0x6000,0x771000)]
def o2r(o):
 for va,sz,rp in secs:
  if rp<=o<rp+sz:return va+o-rp
 return None
def r2o(r):
 for va,sz,rp in secs:
  if va<=r<va+sz:return rp+r-va
 return None
def rd(r):
 o=r2o(r)
 return struct.unpack_from('<I',D,o)[0] if o is not None and o+4<=len(D) else None
# full sentinel census
sent=[]
for off,slot,opc in refs:
 v=rd(slot-IB)
 if v is not None and 0x80000000<=v<=0x8fffffff:
  sent.append((o2r(off),slot,opc,v))
print('sentinel refs',len(sent),'slots',len(set(x[1] for x in sent)),'values',dict(collections.Counter(x[3] for x in sent)))
for x in sent: print('%08X %s slot=%08X val=%08X'%x)

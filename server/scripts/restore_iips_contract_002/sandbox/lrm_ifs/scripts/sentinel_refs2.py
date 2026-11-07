import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
secs=[(0x1000,0x593000,0x1000),(0x8A8000,0x16E000,0x594000),(0xA16000,0x62000,0x702000),(0xE5C8000,0x1000,0x764000),(0xE5C9000,0xA000,0x765000),(0xE5D3000,0x2000,0x76F000),(0xE5D7000,0x6000,0x771000)]
def o2r(o):
 for va,sz,rp in secs:
  if rp<=o<rp+sz:return va+o-rp
 return None
def r2o(r):
 for va,sz,rp in secs:
  if va<=r<va+sz:return rp+r-va
 return None
def rd(va):
 o=r2o(va-IB); return struct.unpack_from('<I',D,o)[0] if o is not None and o+4<=len(D) else None
refs=[]
for off in range(len(D)-6):
 if D[off]==0xFF and D[off+1] in (0x15,0x25):
  refs.append((o2r(off),struct.unpack_from('<I',D,off+2)[0],D[off+1]))
sent=[]
for caller,slot,opc in refs:
 v=rd(slot)
 if v is not None and 0x80000000<=v<=0x8fffffff:sent.append((caller,slot,opc,v))
print('sentinel refs',len(sent),'slots',len(set((x[1],x[3]) for x in sent)))
ctr=collections.Counter((x[1],x[3]) for x in sent)
for (slot,v),n in sorted(ctr.items()):print('slot=%08X val=%08X refs=%d'%(slot,v,n))

import struct,collections
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557;A=0x28
rows=[]; invalid=[]
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43:continue
 raw=A+off; b=d[raw:raw+sz]
 if len(b)<12:
  invalid.append((i,off,sz,'short'));continue
 name_ref,count,ent_ref=struct.unpack_from('<III',b,0)
 if name_ref==0xFFFFFFFF:
  e=b.find(b'\0',12)
  if e<0:invalid.append((i,off,sz,'noname'));continue
  name=b[12:e].decode('latin1','replace'); pos=e+1
 else:
  name='<ref:%08x>'%name_ref; pos=12
 rows.append((i,off,sz,name_ref,count,ent_ref,name,b[pos:]))
print('rows',len(rows),'invalid',len(invalid))
for r in rows[:80]:
 i,off,sz,nr,c,er,nm,pay=r
 print(f'{i:4d} off={off:#08x} sz={sz:4d} count={c:2d} payload={len(pay):4d} name={nm!r} head={pay[:24].hex()}')
print('invalid',invalid[:30])
print('payload lens',collections.Counter(len(r[7]) for r in rows).most_common(20))

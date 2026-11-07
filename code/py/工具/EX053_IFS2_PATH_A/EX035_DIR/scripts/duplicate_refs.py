import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
# find all exact references to duplicate base VA in all common x86 absolute-address encodings
for va in [0x00CA8000,0x00E12944]:
 pat=struct.pack('<I',va)
 poss=[];p=D.find(pat)
 while p>=0:poss.append(p);p=D.find(pat,p+1)
 print('%08X exact dword offsets'%va,['0x%X'%x for x in poss])
# identify section for each
secs=[(0x1000,0x593000,0x1000),(0x8A8000,0x16E000,0x594000),(0xA16000,0x62000,0x702000),(0xE5C8000,0x1000,0x764000),(0xE5C9000,0xA000,0x765000),(0xE5D3000,0x2000,0x76F000),(0xE5D7000,0x6000,0x771000)]
for off in range(len(D)-6):
 # any absolute disp32 whose low 24 bits point near either copy
 for shifts in [2]:
  pass
# scan FF15/25 and mov absolute for all slots around both copies and map to canonical index
for label,base in [('A',0xCA8000),('B',0xE12944)]:
 refs=[]
 for off in range(len(D)-6):
  if D[off]==0xFF and D[off+1] in (0x15,0x25):
   v=struct.unpack_from('<I',D,off+2)[0]
   if base<=v<base+0x768:refs.append(('ff%02x'%D[off+1],off,v))
  elif D[off] in range(0x8B,0x90) and (D[off+1]&0xC7)==0x05:
   v=struct.unpack_from('<I',D,off+2)[0]
   if base<=v<base+0x768:refs.append(('mov',off,v))
 print(label,hex(base),'refs',len(refs),'slots',len(set(x[2] for x in refs)))
 for r in refs[:82]:print(' ',r[0],hex(r[2]))

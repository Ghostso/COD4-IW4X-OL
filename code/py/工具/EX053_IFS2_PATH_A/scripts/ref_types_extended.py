import pathlib,struct,re,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
secs=[(0,'.tp3',0x1000,0x8A689A,0x1000,0x593000,0x60000020),(1,'.tp3',0x8A8000,0x16DA70,0x594000,0x16E000,0x40000040),(2,'.tp3',0xA16000,0xDBB1CC0,0x702000,0x62000,0xC0000040),(3,'.tp3',0xE5C8000,0x31,0x764000,0x1000,0xC0000040),(4,'.tp3',0xE5C9000,0x9228,0x765000,0xA000,0x40000040),(5,'.tvm0',0xE5D3000,0x4000,0x76F000,0x2000,0x60000020),(6,'.tp3',0xE5D7000,0x82000,0x771000,0x6000,0xE0000020)]
def o2r(o):
 for i,n,va,vs,rp,rs,ch in secs:
  if rp<=o<rp+rs:return va+o-rp,i,n
 return None,None,None
def r2o(r):
 for i,n,va,vs,rp,rs,ch in secs:
  if va<=r<va+max(vs,rs):
   x=r-va
   return rp+x if x<rs else None
# byte-pattern refs (not decoded), classify operand and nearby opcode
classes=collections.defaultdict(list)
for off in range(len(D)-6):
 if D[off]==0xFF and D[off+1] in (0x15,0x25):
  va=struct.unpack_from('<I',D,off+2)[0]
  if 0xCA8000<=va<0xCA9400:
   r,i,n=o2r(off); classes['ff%02x'%D[off+1]].append((r,va,off))
 elif D[off] in range(0x8B,0x90): # mov reg, r/m32 is 8B rr; absolute disp32 follows modrm mod00 r/m101
  modrm=D[off+1]
  if (modrm&0xC7)==0x05:
   va=struct.unpack_from('<I',D,off+2)[0]
   if 0xCA8000<=va<0xCA9400:
    r,i,n=o2r(off); classes['mov_load'].append((r,va,off))
# all dword occurrences of slot addresses
for label in ['ff15','ff25','mov_load']:
 print(label,len(classes[label]),'slots',len(set(x[1] for x in classes[label])))
print('all event slot top',[(hex(k),v) for k,v in collections.Counter(x[1] for lab in classes for x in classes[lab]).most_common(40)])
# table slot -> ref types
for va in [0xCA8000,0xCA8004,0xCA8008,0xCA810C,0xCA8114,0xCA8128,0xCA812C,0xCA8164,0xCA819C,0xCA8200,0xCA834C,0xCA84F0,0xCA855C,0xCA8780,0xCA8D10,0xCA93CC]:
 print('%08X value=%08X refs=%s'%(va,struct.unpack_from('<I',D,r2o(va-IB))[0],{lab:sum(x[1]==va for x in ys) for lab,ys in classes.items()}))
# slot address dword occurrences anywhere
print('\nall call/load slots')
for va in sorted(set(x[1] for lab in classes for x in classes[lab])): print('%08X %s'%(va,','.join('%s:%d'%(lab,sum(x[1]==va for x in ys)) for lab,ys in classes.items() if any(x[1]==va for x in ys))))

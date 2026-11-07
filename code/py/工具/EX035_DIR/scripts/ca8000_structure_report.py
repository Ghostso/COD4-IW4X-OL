# -*- coding: utf-8 -*-
"""Read-only structural report for the 0xCA8000 indirect-call slot region."""
import pathlib, struct, collections, math, json
P=pathlib.Path(r'codoMP_client_shipRetail.exe'); D=P.read_bytes(); IB=0x400000; SOI=0x0E659000
SECS=[
 (0,'.tp3',0x00001000,0x08A689A,0x001000,0x593000,0x60000020),
 (1,'.tp3',0x008A8000,0x016DA70,0x594000,0x16E000,0x40000040),
 (2,'.tp3',0x00A16000,0xDBB1CC0,0x702000,0x062000,0xC0000040),
 (3,'.tp3',0x0E5C8000,0x0000031,0x764000,0x001000,0xC0000040),
 (4,'.tp3',0x0E5C9000,0x0009228,0x765000,0x00A000,0x40000040),
 (5,'.tvm0',0x0E5D3000,0x0004000,0x76F000,0x002000,0x60000020),
 (6,'.tp3',0x0E5D7000,0x0082000,0x771000,0x006000,0xE0000020),
]
def sec_of(rva):
 for s in SECS:
  i,n,va,vs,rp,rs,ch=s
  if va<=rva<va+max(vs,rs): return s
 return None
def r2o(rva):
 s=sec_of(rva)
 if not s:return None
 i,n,va,vs,rp,rs,ch=s; x=rva-va
 return rp+x if 0<=x<rs else None
def o2r(o):
 for s in SECS:
  i,n,va,vs,rp,rs,ch=s
  if rp<=o<rp+rs:return va+o-rp
 return None
def hx(x):return '0x%08X'%x
def rdva(va):
 o=r2o(va-IB); return struct.unpack_from('<I',D,o)[0] if o is not None and o+4<=len(D) else None
base=0x00CA8000; base_rva=base-IB; raw=r2o(base_rva)
limit_duplicate=0x768
call_limit=0x75C
# refs by byte pattern
refs=[]
for off in range(len(D)-6):
 if D[off]==0xFF and D[off+1] in (0x15,0x25):
  va=struct.unpack_from('<I',D,off+2)[0]
  if base<=va<base+limit_duplicate:
   refs.append(('ff%02x'%D[off+1],o2r(off),va))
 elif D[off] in range(0x8B,0x90) and (D[off+1]&0xC7)==0x05:
  va=struct.unpack_from('<I',D,off+2)[0]
  if base<=va<base+limit_duplicate:
   refs.append(('mov',o2r(off),va))
by=collections.defaultdict(lambda:collections.Counter())
for typ,ca,slot in refs:by[slot][typ]+=1
allref=set(by); ffslots={s for s in allref if by[s]['ff15'] or by[s]['ff25']}
n=limit_duplicate//4
rows=[]
for i in range(n):
 va=base+4*i; v=rdva(va); r=v-IB if v is not None and IB<=v<IB+SOI else None; s=sec_of(r) if r is not None else None
 rows.append({'i':i,'slot':va,'value':v,'trva':r,'ts':s,'rawback':r2o(r) is not None if r is not None else False,
              'ff15':by[va]['ff15'],'ff25':by[va]['ff25'],'mov':by[va]['mov']})
print('TABLE_BASE %s RVA %s FILEOFF 0x%X SECTION=%s#%d'%(hx(base),hx(base_rva),raw,sec_of(base_rva)[1],sec_of(base_rva)[0]))
print('DUPLICATE_EXTENT bytes=0x%X dwords=%d tail3=%s'%(limit_duplicate,n,' '.join(hx(rows[i]['value']) for i in range(n-3,n))))
print('REF_EVENTS total=%d ff15=%d ff25=%d mov=%d distinct_slots=%d'%(
 len(refs),sum(x[0]=='ff15' for x in refs),sum(x[0]=='ff25' for x in refs),sum(x[0]=='mov' for x in refs),len(allref)))
print('FF_SLOTS=%d FF_EVENTS=%d min=%s max=%s'%(len(ffslots),sum(by[s]['ff15']+by[s]['ff25'] for s in ffslots),hx(min(ffslots)),hx(max(ffslots))))
print('CALL_LIMIT_0x75C_DWORDS=%d last=%s next=%s'%(call_limit//4,hx(base+call_limit-4),hx(base+call_limit)))
# classify all entries and ff-referenced entries
def cls(r):
 v=r['value']
 if v is None:return 'OOB'
 if v==0:return 'ZERO'
 if 0x80000000<=v<=0x8fffffff:return 'SENT'
 if IB<=v<IB+SOI:return 'PTR'
 return 'OTHER'
for label,rr in [('ALL474',rows),('CALLABLE471',rows[:471]),('FF_REF',[r for r in rows if r['slot'] in ffslots]),
                 ('UNION_REF',[r for r in rows if r['slot'] in allref])]:
 print('%s count=%d classes=%s'%(label,len(rr),dict(collections.Counter(cls(r) for r in rr))))
 ptr=[r for r in rr if cls(r)=='PTR']
 if ptr:
  print('  ptr_range=%s..%s target_sections=%s raw_backed=%d low2=%s aligned4=%d'%(
   hx(min(r['value'] for r in ptr)),hx(max(r['value'] for r in ptr)),
   dict(collections.Counter('#%d %s'%(r['ts'][0],r['ts'][1]) for r in ptr)),sum(r['rawback'] for r in ptr),
   dict(collections.Counter(r['value']&3 for r in ptr)),sum(r['value']%4==0 for r in ptr)))
# targets for callable area by 0.25 MiB domain
ptr=[r for r in rows[:471] if cls(r)=='PTR']
dom=collections.Counter((r['value']-IB)//0x40000 for r in ptr)
print('CALLABLE_PTR_256K_BINS')
for k in sorted(dom):print('  %s..%s n=%d'%(hx(IB+k*0x40000),hx(IB+(k+1)*0x40000-1),dom[k]))
# slot value duplicate and FF hotness
vals=collections.Counter(r['value'] for r in rows[:471] if r['value'] is not None)
print('CALLABLE_VALUE_DUPES',[(hx(v),c) for v,c in vals.items() if c>1])
print('FF_TOP',[(hx(s),by[s]['ff15']+by[s]['ff25'],by[s]['mov']) for s,_ in collections.Counter({s:sum(by[s].values()) for s in allref}).most_common(30)])
# sentinel table block shape
print('SENTINEL_BLOCK_CA84B0_CA8564')
for r in rows[(0xCA84B0-base)//4:(0xCA8564-base)//4]:print(' %d %s %s refs=%d/%d/%d'%(r['i'],hx(r['slot']),hx(r['value']),r['ff15'],r['ff25'],r['mov']))
# duplicate copy and refs
copy_off=D.find(D[raw:raw+limit_duplicate],raw+1)
print('DUPLICATE_FILEOFF=0x%X VA=%s REFS=%d'%(copy_off, hx(IB+o2r(copy_off)),sum(1 for _,_,s in refs if IB+o2r(copy_off)<=s<IB+o2r(copy_off)+limit_duplicate)))
# entry descriptor
entry=0x0E5DC690; eslot=0x0E9DC665; eo=r2o(eslot-IB)
print('ENTRY %s bytes=%s slot=%s value=%s fileoff=0x%X'%(hx(entry),D[r2o(entry-IB):r2o(entry-IB)+6].hex(),hx(eslot),hx(struct.unpack_from('<I',D,eo)[0]),eo))
print('ENTRY_NEIGHBOR_ALIGNED_DWORDS')
for va in range(eslot-0x10,eslot+0x14,4):
 print('  %s %s'%(hx(va),hx(rdva(va))))
pat=bytes.fromhex('FF1565C69D0E')
print('ENTRY_PATTERN_OCCURRENCES',D.count(pat),'OPERAND_DWORD_OCCURRENCES',D.count(struct.pack('<I',eslot)))

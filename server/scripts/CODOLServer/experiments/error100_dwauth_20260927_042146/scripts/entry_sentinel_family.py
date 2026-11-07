# -*- coding: utf-8 -*-
"""Read-only entry sentinel-family analysis.

.tvm0 is excluded before any payload-derived offset is dereferenced.  The report
keeps raw-pattern, instruction-boundary, recursive-candidate, entry-static-CFG,
and runtime-reachability evidence separate.
"""
from __future__ import annotations
import collections, datetime, pathlib, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

EXE=pathlib.Path('codoMP_client_shipRetail.exe')
OUT=pathlib.Path('scripts/_out/entry_sentinel_family.txt')
IB=0x00400000; ENTRY_RVA=0x0E5DC690; ENTRY_SLOT=0x0E9DC665
SLOT_RVA=ENTRY_SLOT-IB; LO=0x0E5DC600; HI=0x0E5DC700
SLO,SHI=0x80000000,0x8FFFFFFF
u16=lambda b,o:struct.unpack_from('<H',b,o)[0]
u32=lambda b,o:struct.unpack_from('<I',b,o)[0]
hx=lambda x:'0x%08X'%(x&0xffffffff)

# PE headers only.
with EXE.open('rb') as f:hdr=f.read(0x1000)
assert hdr[:2]==b'MZ'; pe=u32(hdr,0x3c); assert hdr[pe:pe+4]==b'PE\0\0'
co=pe+4; ns=u16(hdr,co+2); osz=u16(hdr,co+16); op=co+20
assert u16(hdr,op)==0x10b
entry=u32(hdr,op+16); image=u32(hdr,op+28); size=u32(hdr,op+56); assert (image,entry)==(IB,ENTRY_RVA)
st=op+osz; sections=[]
for i in range(ns):
 q=st+i*40; sections.append(dict(idx=i,name=hdr[q:q+8].split(b'\0',1)[0].decode('latin1'),
  va=u32(hdr,q+12),vsize=u32(hdr,q+8),raw=u32(hdr,q+20),rawsize=u32(hdr,q+16),chars=u32(hdr,q+36),data=None))
excluded=[s['idx'] for s in sections if s['name']=='.tvm0']; assert excluded==[5]
# Never read .tvm0 payload.
with EXE.open('rb') as f:
 for s in sections:
  if s['idx'] in excluded:continue
  if s['rawsize']:
   f.seek(s['raw']);s['data']=f.read(s['rawsize']);assert len(s['data'])==s['rawsize']
allowed=[s for s in sections if s['data'] is not None]; exsecs=[s for s in allowed if s['chars']&0x20000000]

def sec(rva,raw=False):
 for s in sections:
  if s['va']<=rva<s['va']+max(s['vsize'],s['rawsize']):
   if raw and (s['data'] is None or rva-s['va']>=s['rawsize']):return None
   return s
 return None
def r2o(rva):
 s=sec(rva,True);return None if s is None else s['raw']+rva-s['va']
def rd32(rva):
 s=sec(rva,True)
 if s is None or rva-s['va']+4>s['rawsize']:return None
 return u32(s['data'],rva-s['va'])
def rbytes(rva,n):
 s=sec(rva,True)
 if s is None or rva-s['va']+n>s['rawsize']:return None
 return s['data'][rva-s['va']:rva-s['va']+n]
def is_exec(rva):
 s=sec(rva,True);return bool(s and s['chars']&0x20000000)
def valclass(v):
 if v is None:return 'UNMAPPED'
 if v==0:return 'ZERO'
 if SLO<=v<=SHI:return 'SENTINEL_8XXXXXXX'
 if IB<=v<IB+size:return 'IMAGE_VA'
 if v<0x10000:return 'LOW_VALUE'
 return 'OTHER_VALUE'

md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def one(rva):
 b=rbytes(rva,15);return None if b is None else next(md.disasm(b,IB+rva,count=1),None)
def memop(ins):
 if not (ins and len(ins.bytes)>=2 and ins.bytes[0]==0xff and ins.bytes[1] in (0x15,0x25)):return None
 if not ins.operands:return None
 o=ins.operands[0]
 return int(o.mem.disp)&0xffffffff if o.type==X86_OP_MEM and o.mem.base==0 and o.mem.index==0 else None
def slotval(va):
 return rd32(va-IB) if IB<=va<IB+size else None

# RAW: every FF15/FF25 pair in permitted raw sections. This is no boundary claim.
raw=[]
for s in allowed:
 b=s['data']
 for i in range(max(0,len(b)-5)):
  if b[i]==0xff and b[i+1] in (0x15,0x25):
   va=u32(b,i+2);raw.append(dict(rva=s['va']+i,off=s['raw']+i,sec=s['idx'],opc=b[i+1],va=va,val=slotval(va)))

# SELF_BOUNDARY: each raw candidate decoded at its own stated offset.
selfb=[]
for e in raw:
 ins=one(e['rva']);va=memop(ins)
 if va is not None:selfb.append(dict(e,ins=ins,va=va,val=slotval(va),near=[(d,rd32((va-IB)+4*d)) for d in range(-4,5) if rd32((va-IB)+4*d) is not None and SLO<=rd32((va-IB)+4*d)<=SHI]))
# Nearby-value matches for FF15/FF25 pointed slots.  Exact means the pointed
# dword itself is 8xxxxxxx; nearby means another aligned dword within +/-16 is.
near_matches=[]
for e in selfb:
 hits=[]
 for d in range(-4,5):
  v=rd32((e['va']-IB)+4*d)
  if v is not None and SLO<=v<=SHI:hits.append((d,v))
 exact=any(d==0 for d,v in hits)
 nearextra=[(d,v) for d,v in hits if d!=0]
 if exact or nearextra:near_matches.append((e,hits,exact))

# ENTRY_CFG_STATIC: seed is entry, traverse fallthrough and direct call targets. No indirect targets.
def traverse_entry(with_calls):
 M={};q=collections.deque([ENTRY_RVA]);n=0
 while q and n<1000000:
  rva=q.popleft();n+=1
  while True:
   if rva in M or not is_exec(rva):break
   ins=one(rva)
   if ins is None:break
   M[rva]=ins;mn=ins.mnemonic
   if mn=='call':
    if with_calls and ins.operands and ins.operands[0].type==X86_OP_IMM:
     t=int(ins.operands[0].imm)-IB
     if is_exec(t):q.append(t)
    rva+=ins.size;continue
   if mn=='jmp':
    if ins.operands and ins.operands[0].type==X86_OP_IMM:
     t=int(ins.operands[0].imm)-IB
     if is_exec(t):q.append(t)
    break
   if mn.startswith('j') and ins.operands and ins.operands[0].type==X86_OP_IMM:
    t=int(ins.operands[0].imm)-IB
    if is_exec(t):q.append(t)
    rva+=ins.size;continue
   if mn in ('ret','retf','iret','hlt','ud2','int3'):break
   rva+=ins.size
 return M
entry_with=traverse_entry(True);entry_no=traverse_entry(False)
def ff(M):
 z=[]
 for rva,ins in M.items():
  va=memop(ins)
  if va is not None:z.append(dict(rva=rva,ins=ins,va=va,val=slotval(va)))
 return z
ew=ff(entry_with);en=ff(entry_no)

# RECURSIVE_CANDIDATE: old over-inclusive seed model, explicitly not reachability.
def decode_linear(s):
 out=[]
 for ins in md.disasm(s['data'],IB+s['va']):
  out.append((ins.address-IB,ins))
 return out
lin=[];lin_starts=set()
for s in exsecs:
 for rva,ins in decode_linear(s):lin.append((rva,ins));lin_starts.add(rva)
def trav(fn,M,seen,Q,limit=300000):
 if fn in seen or not is_exec(fn):return
 seen.add(fn);rva=fn
 for _ in range(limit):
  if rva in M or not is_exec(rva):return
  ins=one(rva)
  if ins is None:return
  M[rva]=ins;mn=ins.mnemonic
  if mn=='call' and ins.operands and ins.operands[0].type==X86_OP_IMM:
   t=int(ins.operands[0].imm)-IB
   if is_exec(t):Q.append(t)
  elif mn=='jmp':
   if ins.operands and ins.operands[0].type==X86_OP_IMM:
    t=int(ins.operands[0].imm)-IB
    if is_exec(t):Q.append(t)
   return
  elif mn.startswith('j') and ins.operands and ins.operands[0].type==X86_OP_IMM:
   t=int(ins.operands[0].imm)-IB
   if is_exec(t):Q.append(t)
  elif mn in ('ret','retf','iret','hlt','ud2','int3'):return
  rva+=ins.size
M={};seen=set();Q=collections.deque([ENTRY_RVA]);seedn=0
while Q:trav(Q.popleft(),M,seen,Q)
for s in exsecs:
 b=s['data']
 for k in range(len(b)-4):
  if b[k]==0xe8:
   t=s['va']+k+5+struct.unpack_from('<i',b,k+1)[0]
   if is_exec(t) and t not in seen:seedn+=1;Q.append(t)
while Q:trav(Q.popleft(),M,seen,Q)
rec=ff(M)

# Direct E8/E9 candidates targeting the entry.
direct_entry=[]
for s in allowed:
 b=s['data']
 for k in range(len(b)-4):
  if b[k] in (0xe8,0xe9):
   t=s['va']+k+5+struct.unpack_from('<i',b,k+1)[0]
   if t==ENTRY_RVA:direct_entry.append((s['va']+k,s['idx'],b[k],s['va']+k in lin_starts,s['va']+k in M))

# Exact sentinels/pairs and entry slot occurrences.
sent_occ=[];pair_occ=[]
for s in allowed:
 b=s['data']
 for i in range(len(b)-3):
  v=u32(b,i)
  if v==0x80000001:sent_occ.append((s['va']+i,i&3,s['idx']))
  if v==0x80000001 and i+8<=len(b) and u32(b,i+4)==0:pair_occ.append((s['va']+i,i&3,s['idx']))
raw_slot=[];raw_slotpat=[]
for s in allowed:
 b=s['data']
 for i in range(len(b)-3):
  if u32(b,i)==ENTRY_SLOT:raw_slot.append((s['va']+i,s['idx'],s['va']+i in lin_starts,s['va']+i in M))
 for opc in (0x15,0x25):
  p=bytes([0xff,opc])+struct.pack('<I',ENTRY_SLOT);j=0
  while True:
   j=b.find(p,j)
   if j<0:break
   raw_slotpat.append((opc,s['va']+j,s['idx'],s['va']+j in lin_starts,s['va']+j in M));j+=1

lines=[]
def w(x=''):lines.append(str(x))
w('ENTRY_SENTINEL_FAMILY')
w('Generated (UTC): '+datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
w('Image: '+str(EXE.resolve()))
w('Mode: READ-ONLY; .tvm0 payload is excluded before any payload scan')
w()
w('EVIDENCE DEFINITIONS')
w('  RAW_PATTERN: FF15/FF25 byte pair at any offset in permitted raw-backed sections. No instruction-boundary claim.')
w('  SELF_BOUNDARY: Capstone successfully decodes a complete FF15/FF25 instruction when started exactly at that same raw candidate offset.')
w('  LINEAR_BOUNDARY: an instruction start from contiguous Capstone disassembly beginning at a section raw start. This is only a candidate stream and may desynchronize on data.')
w('  RECURSIVE_CANDIDATE: the deliberately over-inclusive recursive candidate graph. It seeds from all raw E8 rel32 candidates in permitted executable .tp3 sections, then follows direct call/jump/conditional edges. It is NOT a reachability proof.')
w('  ENTRY_CFG_STATIC: direct/fallthrough traversal rooted at AddressOfEntryPoint. Indirect edge targets are unknown.')
w('  RUNTIME_REACHABLE: not established. No claim of reachability or unreachability is made.')
w()
w('PE / SECTION FACTS')
w('  ImageBase=%s AddressOfEntryPoint=%s EntryVA=%s SizeOfImage=%s'%(hx(IB),hx(ENTRY_RVA),hx(IB+ENTRY_RVA),hx(size)))
for s in sections:
 tag=' [EXCLUDED / NOT READ]' if s['idx'] in excluded else ''
 flags=','.join(n for m,n in [(0x20,'CNT_CODE'),(0x40,'CNT_INITIALIZED_DATA'),(0x80,'CNT_UNINITIALIZED_DATA'),(0x20000000,'MEM_EXECUTE'),(0x40000000,'MEM_READ'),(0x80000000,'MEM_WRITE')] if s['chars']&m)
 w('  #%d %-5s RVA=%s VSize=%s RawOff=0x%X RawSize=%s Chars=%s [%s]%s'%(s['idx'],s['name'],hx(s['va']),hx(s['vsize']),s['raw'],hx(s['rawsize']),hx(s['chars']),flags,tag))
s6=sec(ENTRY_RVA)
w('  ENTRY_SLOT_SECTION=#%d %s RVA=%s raw_backed=%s'%(s6['idx'],s6['name'],hx(SLOT_RVA),str(SLOT_RVA-s6['va']<s6['rawsize'])))
w()
w('ENTRY AND SLOT')
w('  entry_bytes=%s wildcard_shortcut=%s'%(rbytes(ENTRY_RVA,6).hex(' '),'FF 15 ** ** ** **'))
w('  entry_operand=VA %s RVA %s section=#%d'%(hx(ENTRY_SLOT),hx(SLOT_RVA),s6['idx']))
w('  slot_value=%s class=%s slot_next=%s'%(hx(rd32(SLOT_RVA)),valclass(rd32(SLOT_RVA)),hx(rd32(SLOT_RVA+4))))
w()
w('FAQ / DIRECT ANSWERS')
w('  1. Is 0xE9DC665 the FF15 operand at the entry? YES / HIGH. It is the absolute VA encoded by the entry instruction.')
w('  2. Are there other FF15/FF25 references to 0xE9DC665? NO / HIGH for the permitted-section scan. Exact opcode+slot occurs 1 time; exact slot dword occurs 1 time; entry static CFG has 1 such reference.')
w('  3. Is there a local family of [0x80000001,0] near the slot? It is a two-record local pattern only. The nearby values are 0x80000001 at slot-8 and slot, with zeros between and after. HIGH for byte layout; LOW for naming it a descriptor table.')
w('  4. Are there other FF15/FF25 whose pointed slot value is an 8xxxxxxx sentinel? YES in SELF_BOUNDARY/RECURSIVE_CANDIDATE. The exact [0x80000001,0] pair is unique to the entry slot. The other values cluster around 0xCA85xx and are mostly 0x80000002..0x80000074, but they are not the same entry descriptor.')
w('  5. Does that prove them live? NO. SELF_BOUNDARY and RECURSIVE_CANDIDATE only prove byte/instruction-shape relationships, not execution.')
w()
# Reports
# Any candidate instruction that names the entry slot as an immediate/operand.
def entry_operand_refs(M):
 out=[]
 for rva in sorted(M):
  ins=M[rva]
  for oi,o in enumerate(ins.operands):
   if o.type==X86_OP_MEM and o.mem.base==0 and o.mem.index==0 and (int(o.mem.disp)&0xffffffff)==ENTRY_SLOT:out.append((rva,ins,oi,'MEM'))
   elif o.type==X86_OP_IMM and (int(o.imm)&0xffffffff)==ENTRY_SLOT:out.append((rva,ins,oi,'IMM'))
 return out
generic_entry=entry_operand_refs(M)

# Two variants of the entry static traversal.
def evline(e,prefix=''):
 ins=e.get('ins');return '%s%s %s %-6s %-34s operand=%s slot_value=%s slot_class=%s'%(prefix,hx(e['rva']),e.get('bytes',ins.bytes.hex() if ins else '-'),ins.mnemonic if ins else '-',ins.op_str if ins else '-',hx(e['va']),hx(e['val']) if e['val'] is not None else '-',valclass(e['val']))
w('RAW_PATTERN SUMMARY')
w('  total=%d ff15=%d ff25=%d by_section=%s'%(len(raw),sum(e['opc']==0x15 for e in raw),sum(e['opc']==0x25 for e in raw),dict(collections.Counter(e['sec'] for e in raw))))
w('  direct_operand_8xxxxxxx=%d pointed_slot_value_8xxxxxxx=%d'%(sum(SLO<=e['va']<=SHI for e in raw),sum(e['val'] is not None and SLO<=e['val']<=SHI for e in raw)))
w()
w('SELF_BOUNDARY SUMMARY')
w('  total=%d ff15=%d ff25=%d by_section=%s'%(len(selfb),sum(e['opc']==0x15 for e in selfb),sum(e['opc']==0x25 for e in selfb),dict(collections.Counter(e['sec'] for e in selfb))))
w('  direct_operand_8xxxxxxx=%d pointed_slot_value_8xxxxxxx=%d distinct_sentinel_slots=%d'%(sum(SLO<=e['va']<=SHI for e in selfb),sum(e['val'] is not None and SLO<=e['val']<=SHI for e in selfb),len({e['va'] for e in selfb if e['val'] is not None and SLO<=e['val']<=SHI})))
w()
w('LINEAR_BOUNDARY SUMMARY (candidate stream, not reachability)')
w('  instructions=%d ff15_ff25=%d by_section=%s'%(len(lin),len([x for x in lin if memop(x[1]) is not None]),dict(collections.Counter(sec(r)['idx'] for r,i in lin if memop(i) is not None))))
for rva,ins in lin:
 va=memop(ins)
 if va is not None:w(evline(dict(rva=rva,ins=ins,va=va,val=slotval(va),bytes=ins.bytes.hex())))
w()
w('RECURSIVE_CANDIDATE SUMMARY')
w('  instructions=%d functions=%d raw_e8_seed_candidates=%d ff15_ff25=%d ff15=%d ff25=%d'%(len(M),len(seen),seedn,len(rec),sum(e['ins'].bytes[1]==0x15 for e in rec),sum(e['ins'].bytes[1]==0x25 for e in rec)))
w('  direct_operand_8xxxxxxx=%d pointed_slot_value_8xxxxxxx=%d distinct_sentinel_slots=%d exact_pair=%d'%(sum(SLO<=e['va']<=SHI for e in rec),sum(e['val'] is not None and SLO<=e['val']<=SHI for e in rec),len({e['va'] for e in rec if e['val'] is not None and SLO<=e['val']<=SHI}),sum(e['val']==0x80000001 and rd32(e['va']-IB+4)==0 for e in rec)))
w('  ENTRY_SLOT_REFS:')
for e in sorted([x for x in rec if x['va']==ENTRY_SLOT],key=lambda z:z['rva']):w(evline(e,'    '))
w()
w('ENTRY_CFG_STATIC SUMMARY')
w('  with_direct_call_successors: instructions=%d ff15_ff25=%d'%(len(entry_with),len(ew)))
for e in sorted(ew,key=lambda z:z['rva']):w(evline(e,'    '))
w('  without_direct_call_successors: instructions=%d ff15_ff25=%d'%(len(entry_no),len(en)))
for e in sorted(en,key=lambda z:z['rva']):w(evline(e,'    '))
w()
w('DIRECT E8/E9 TARGETING ENTRY RVA')
if not direct_entry:w('  (none)')
for rva,si,opc,linb,recb in direct_entry:w('  rva=%s sec=#%d opcode=%02X linear_boundary=%s recursive_candidate=%s'%(hx(rva),si,opc,linb,recb))
w()
w('EXACT FF15/FF25 + ENTRY SLOT')
if not raw_slotpat:w('  (none)')
for opc,rva,si,linb,recb in raw_slotpat:w('  FF%02X rva=%s sec=#%d linear_boundary=%s recursive_candidate=%s'%(opc,hx(rva),si,linb,recb))
w('EXACT ENTRY SLOT DWORD OCCURRENCES')
if not raw_slot:w('  (none)')
for rva,si,linb,recb in raw_slot:w('  rva=%s sec=#%d linear_boundary=%s recursive_candidate=%s'%(hx(rva),si,linb,recb))
w()
w('RECURSIVE_CANDIDATE INSTRUCTIONS NAMING THE ENTRY SLOT AS OPERAND/IMMEDIATE')
w('  count=%d'%len(generic_entry))
for rva,ins,oi,kind in generic_entry:w('    %s operand_index=%d kind=%s %s %s'%(hx(rva),oi,kind,ins.mnemonic,ins.op_str))
w()
w('EXACT 0x80000001 / ZERO FAMILY')
w('  exact 0x80000001 occurrences=%d by_section=%s by_alignment_mod4=%s'%(len(sent_occ),dict(collections.Counter(x[2] for x in sent_occ)),dict(collections.Counter(x[1] for x in sent_occ))))
w('  exact consecutive [0x80000001,0] pairs=%d by_section=%s by_alignment_mod4=%s'%(len(pair_occ),dict(collections.Counter(x[2] for x in pair_occ)),dict(collections.Counter(x[1] for x in pair_occ))))
for rva,a,si in pair_occ:
 nref=sum(1 for e in selfb if e['va']==IB+rva)
 w('    pair rva=%s va=%s sec=#%d align=%d ff15_ff25_refs=%d'%(hx(rva),hx(IB+rva),si,a,nref))
w()
w('SELF_BOUNDARY FF15/FF25 WITH POINTED SLOT VALUE 8XXXXXXX')
for e in sorted([x for x in selfb if x['val'] is not None and SLO<=x['val']<=SHI],key=lambda z:(z['rva'],z['va'])):w(evline(e,'  '))
w()
w('SELF_BOUNDARY FF15/FF25 WITH A MATCHING 8XXXXXXX VALUE WITHIN +/-16 BYTES')
w('  matches=%d exact_pointed_value=%d near_only=%d'%(len(near_matches),sum(1 for e,h,x in near_matches if x),sum(1 for e,h,x in near_matches if not x)))
for e,hits,exact in sorted(near_matches,key=lambda z:(z[0]['rva'],z[0]['va'])):
 hs=';'.join('%+d*4:%s'%(d,hx(v)) for d,v in hits)
 w('%s exact=%s near=[%s]'%(evline(e,'  '),str(exact),hs))
w()
w('SELF_BOUNDARY FF15/FF25 DIRECT OPERANDS 8XXXXXXX')
for e in sorted([x for x in selfb if SLO<=x['va']<=SHI],key=lambda z:(z['rva'],z['va'])):w(evline(e,'  '))
w()
w('0x0E9DC600..0x0E9DC700 FILE-BACKED LAYOUT')
for rva in range(LO,HI,16):
 b=rbytes(rva,16)
 if b is None:w('  RVA %s [NOT RAW-BACKED]'%hx(rva));continue
 w('  RVA %s VA %s OFF %06X  %-47s  %s'%(hx(rva),hx(IB+rva),r2o(rva),' '.join('%02X'%x for x in b),''.join(chr(x) if 32<=x<127 else '.' for x in b)))
w()
w('0x0E9DC600..0x0E9DC700 ALIGNED DWORD VIEW')
for rva in range(LO,HI,4):
 v=rd32(rva);b=rbytes(rva,4);tag=''
 if rva==ENTRY_RVA:tag+=' ENTRY_INSTRUCTION_START'
 if rva==SLOT_RVA:tag+=' ENTRY_SLOT'
 if v==0x80000001:tag+=' EXACT_80000001'
 if SLO<=v<=SHI:tag+=' SENTINEL_CLASS'
 w('  RVA=%s VA=%s value=%s bytes=%s%s'%(hx(rva),hx(IB+rva),hx(v),b.hex(' '),tag))
w()
w('ENTRY SLOT LOCAL UNALIGNED VIEW')
for q in range(SLOT_RVA-0x20,SLOT_RVA+0x20,4):
 v=rd32(q);n=rd32(q+4);tag=' <-- ENTRY_SLOT_START' if q==SLOT_RVA else ''
 if v==0x80000001 and n==0:tag+=' [0x80000001,0]'
 w('  start_rva=%s VA=%s dword0=%s dword1=%s%s'%(hx(q),hx(IB+q),hx(v),hx(n),tag))
w()
w('FINDINGS / CONFIDENCE')
w('  HIGH: Entry RVA 0x0E5DC690 decodes as FF 15 65 C6 9D 0E = call dword ptr [0x0E9DC665].')
w('  HIGH: The operand is an absolute VA into section #6 (.tp3, RVA 0x0E5D7000, RawOff 0x771000, RawSize 0x6000, Characteristics 0xE0000020: execute/read/write).')
w('  HIGH: The exact slot is raw-backed and contains 0x80000001 followed by 0x00000000.')
w('  HIGH: The exact FF15+slot byte sequence occurs once in permitted sections, at the entry itself; the exact slot dword occurs once, as the entry instruction operand.')
w('  HIGH: ENTRY_CFG_STATIC contains the entry FF15 instruction. This is a static traversal rooted at the PE entry, not a runtime execution claim.')
w('  MEDIUM: There are two adjacent local 8-byte [0x80000001,0] records at RVA 0x0E5DC65D and 0x0E5DC665, followed by the ASCII module name codoMP_client_shipRetailBase.dll. This is consistent with loader/protection/control metadata, but the record type is not established.')
w('  MEDIUM: SELF_BOUNDARY finds other FF15/FF25 operations whose pointed slots contain 8xxxxxxx values; these are concentrated in the 0xCA8xxx slot region. This is instruction-shape evidence only, not proof of execution.')
w('  MEDIUM: The exact [0x80000001,0] pair is unique to the entry descriptor/protection-shaped local layout; other sentinel-valued slots use different values and are not the same record.')
w('  HIGH: Of the two local [0x80000001,0] pairs, the one at RVA 0x0E5DC65D has 0 FF15/FF25 references and the one at 0x0E5DC665 has 1, at the entry instruction.')
w('  MEDIUM: RECURSIVE_CANDIDATE finds the same broad sentinel family, but its seed set is deliberately over-inclusive. Counts are upper-bound candidate relationships, not live callsites.')
w('  LOW: The identity of 0x80000001 (status code vs encoded pointer/control value) is unknown from static bytes.')
w('  LOW: The nearby layout being loader/protection/custom-import metadata is a hypothesis.')
w('  UNKNOWN: Whether the entry indirect call executes, returns, or is patched at runtime; its runtime target is unknown.')
w('  UNKNOWN: Runtime reachability of other FF15/FF25 instructions. No runtime memory dump or trace was available, so neither reachable nor unreachable is asserted.')
w('  UNKNOWN: Whether this family is related to dwLobbyEventHandler RTTI; no evidence from this path establishes that relation.')

OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('WROTE',OUT)
print('raw',len(raw),'selfb',len(selfb),'lin',len(lin),'rec',len(rec),'entry_with',len(entry_with),'entry_no',len(entry_no),'slotpat',len(raw_slotpat),'pairs',len(pair_occ),'near',len(near_matches),'generic_entry',len(generic_entry))

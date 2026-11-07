import csv, struct, collections
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
D=Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
pe=struct.unpack_from('<I',D,0x3c)[0]; ns=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; oh=struct.unpack_from('<H',D,pe+20)[0]; so=opt+oh
SEC=[]
for i in range(ns):
 h=so+40*i; name=D[h:h+8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); ch=struct.unpack_from('<I',D,h+36)[0]; SEC.append(dict(i=i,name=name,va=va,vs=vs,rs=rs,pr=pr,ch=ch))
def sec(r):
 for s in SEC:
  if s['va']<=r<s['va']+max(s['vs'],s['rs']): return s
def off(r):
 s=sec(r)
 if not s:return None
 q=r-s['va']; return s['pr']+q if 0<=q<s['rs'] else None
def u32(r):
 f=off(r); return struct.unpack_from('<I',D,f)[0] if f is not None and f+4<=len(D) else None
def is_exec(r):
 s=sec(r); return bool(s and s['name']!='.tvm0' and s['ch']&0x20000000 and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
rows=list(csv.DictReader(open(r'scripts\_out\high_reuse_slot_detail.csv',encoding='utf-8')))
seen=[]
for r in rows:
 fn=r['candidate_func']
 if fn and fn not in seen: seen.append(fn)
print('candidate starts',len(seen))
for fn in seen:
 st=int(fn,16)
 if st == 0x36490: continue
 f=off(st); ref=int(next(r['ref_rva'] for r in rows if r['candidate_func']==fn),16); xx=list(md.disasm(D[max(0,f-64):off(ref)+16],IB+max(st-64,0)))
 print('\n%s kind=%s refs=%s context=%s'%(fn,next(r['candidate_kind'] for r in rows if r['candidate_func']==fn),' '.join(r['ref_rva'] for r in rows if r['candidate_func']==fn),D[max(0,f-8):f+24].hex()))
 for x in xx:
  if ref-64 <= x.address-IB <= ref+16: print('  %08X %-20s %s %s%s'%(x.address-IB,x.bytes.hex(),x.mnemonic,x.op_str,' <== REF' if x.address-IB==ref else ''))

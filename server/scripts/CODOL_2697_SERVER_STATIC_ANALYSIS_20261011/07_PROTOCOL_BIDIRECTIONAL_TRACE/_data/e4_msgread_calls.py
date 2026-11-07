import sys,os,struct,bisect
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
im=c.load(c.CLIENT_CAND);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# all direct calls from executable sections, normalized on both VA and RVA interpretation
insns={}
for nm,va,vs,pt,rs in im.sections:
 if nm not in ('.text','.tvm0') or not rs: continue
 for ins in md.disasm(im.data[pt:pt+rs],im.ib+va): insns[ins.address-im.ib]=ins
rawcalls=[]
for nm,va,vs,pt,rs in im.sections:
 if nm not in ('.text','.tvm0') or not rs: continue
 for i in range(pt,pt+rs-5):
  if im.data[i]==0xe8:
   src=va+(i-pt); rel=struct.unpack_from('<i',im.data,i+1)[0]; dest=src+5+rel
   rawcalls.append((src,dest))
print('rawcalls',len(rawcalls))
for t in [0x1AC1D0,0x1ACB00,0x23CB50,0x23C7F0,0x1B1F20,0x1E94F0,0x236FC0]:
 hits=[(s,d) for s,d in rawcalls if d==t]
 print('CALL TARGET RVA %X raw hits %d'%(t,len(hits)),[(hex(s),hex(d)) for s,d in hits[:100]])
 for va in [0x400000+t,0x400000+0x1000+t]:
  hits2=[(s,d) for s,d in rawcalls if d==va]
  if hits2: print(' abs variant',hex(va),[(hex(s),hex(d)) for s,d in hits2[:80]])
# inspect 1acb00 function
for r in [0x1AC1D0,0x1ACB00,0x1AC1D0,0x1ACA10,0x1ACB00]:
 print('\nDIS',hex(r))
 for ins in im.disasm(r,count=100): print(' %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))

import pefile, struct
from capstone import *
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
text=[s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text'][0]
raw=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
base=pe.OPTIONAL_HEADER.ImageBase+text.VirtualAddress
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
import collections,time
cnt=collections.Counter(); t0=time.time(); n=0
for ins in md.disasm(raw,base):
    n+=1
    for op in ins.operands:
        if op.type==CS_OP_MEM and op.mem.base==0 and op.mem.index==0:
            a=op.mem.disp & 0xffffffff
            if 0x400000<=a<0xEA59000: cnt[a]+=1
print('insns',n,'time',round(time.time()-t0,1))
print('unique exe-range data refs:',len(cnt),'total refs:',sum(cnt.values()))
for a,c in cnt.most_common(25): print('  %#010x  %d'%(a,c))

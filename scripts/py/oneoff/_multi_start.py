from pathlib import Path
from capstone import *
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes(); base=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
starts=[0x3664d,0x36656,0x36661,0x36665,0x3666f,0x36670,0x36675,0x3667a,0x36680,0x36689,0x36691,0x36697,0x3669c,0x366a9,0x366ab,0x366b5,0x366c6,0x366cd]
ins={}
for st in starts:
 seq=[]
 for x in md.disasm(D[st:st+160],base+st):
  seq.append((x.address-base,x.bytes.hex(),x.mnemonic,x.op_str))
  if x.mnemonic.startswith('ret') or x.mnemonic in ('jmp','ud2','int3'): break
 ins[st]=seq
for st,seq in ins.items():
 print('===',hex(st),'===')
 for r,b,m,o in seq: print(f'{r:08X} {b:<18} {m:<8} {o}')

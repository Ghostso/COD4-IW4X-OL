import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
# Enumerate indirect jumps [reg*4+disp32] in text and validate table targets as text-range addresses
results=[]
for i in range(0x1000,min(len(b),0x8a6000)-7):
 if b[i:i+2]==b'\xff\x24':
  # ff 24 85/8d/95/9d disp32 forms; decode via capstone
  ins=list(md.disasm(b[i:i+7],IB+i))
  if not ins:continue
  x=ins[0]
  if x.mnemonic=='jmp' and 'dword ptr' in x.op_str and '*4' in x.op_str:
   # find final displacement in instruction encoding
   disp=None
   if b[i+2]&0xc7==0x85:
    disp=struct.unpack_from('<I',b,i+3)[0]
   if disp is None:continue
   # treat disp as VA or RVA heuristically
   targets=[]
   for base in (0,IB):
    tab=disp-base
    if 0<=tab<len(b)-1024:
     vals=[struct.unpack_from('<I',b,tab+j*4)[0] for j in range(32)]
     vals_in=[v-IB for v in vals if 0x1000<=v-IB<0x8a6000]
     targets.append((base,tab,len(vals_in)))
   results.append((i,x.bytes.hex(),x.op_str,disp,targets))
print('indirect jmp [*4+disp] count',len(results))
for r in results[:200]:
 print(hex(r[0]),r[1],r[2],hex(r[3]),r[4])
# specifically the two known tables from 5F830 and 2000A0 with correct interpretation
print('\nknown table probes')
for tab in [0x46040c,0x46068c,0x200744]:
 vals=[struct.unpack_from('<I',b,tab+j*4)[0] for j in range(64)]
 print(hex(tab),'as VA:',[hex(v) for v in vals[:12]],'in-text:',sum(1 for v in vals if 0x400000<=v<0xCA6000))

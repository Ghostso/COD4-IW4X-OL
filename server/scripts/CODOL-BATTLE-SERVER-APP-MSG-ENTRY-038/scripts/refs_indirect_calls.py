import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
# callers of parser family by direct E8 and by VA data pointer references
def callers(t):
 out=[]
 for i in range(0x1000,min(len(b),0x8a6000)-5):
  if b[i]==0xe8:
   rel=struct.unpack_from('<i',b,i+1)[0]
   if i+5+rel==t:out.append(i)
 return out
def ptrrefs(t):
 va=IB+t;out=[]
 pat=struct.pack('<I',va)
 start=0
 while True:
  j=b.find(pat,start)
  if j<0:break
  out.append(j);start=j+1
 return out
for t in [0x6D060,0x6D360,0x6D6E0,0x6D870,0x6D960,0x6D9D0,0x6DA30,0x6DAE0,0x6DCF0,0x6E030,0x6E0A0,0x5F830,0x1FF820,0x208380,0x5FF820,0x2000A0]:
 c=callers(t);p=ptrrefs(t)
 print(f'{t:#x}: direct_calls={[hex(x) for x in c]} ptr_refs={[hex(x) for x in p[:12]]} ptr_count={len(p)}')
# dump all indirect calls [reg*4+disp] with valid table targets in text
ind=[]
for i in range(0x1000,min(len(b),0x8a6000)-7):
 if b[i:i+2]==b'\xff\x14':
  ins=list(md.disasm(b[i:i+7],IB+i))
  if ins and ins[0].mnemonic=='call':
   x=ins[0]
   if '*4' in x.op_str:
    disp=struct.unpack_from('<I',b,i+3)[0]
    if disp>=IB:
     tab=disp-IB
     vals=[struct.unpack_from('<I',b,tab+j*4)[0] for j in range(32)]
     good=sum(1 for v in vals if IB+0x1000<=v<IB+0x8a6000)
     if good>=2:ind.append((i,tab,good,x.op_str))
print('\nindirect call tables with valid VA targets:',len(ind))
for x in ind[:160]:print(hex(x[0]),hex(x[1]),x[2],x[3])
json.dump(ind,open(r'D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOL-BATTLE-SERVER-APP-MSG-ENTRY-038\\evidence\\indirect_call_tables.json','w'),indent=2)

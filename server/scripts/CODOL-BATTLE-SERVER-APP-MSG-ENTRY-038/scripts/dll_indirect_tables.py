import struct,capstone,json
p=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(p,'rb').read();IB=0x10000000
# section map
E=struct.unpack_from('<I',b,0x3c)[0];C=E+4;NS=struct.unpack_from('<H',b,C+2)[0];OP=struct.unpack_from('<H',b,C+16)[0];S=C+20+OP
secs=[]
for i in range(NS):
 q=S+i*40;nm=b[q:q+8].split(b'\0')[0].decode('latin1');vs,va,rs,ptr=struct.unpack_from('<IIII',b,q+8);secs.append((nm,va,vs,ptr,rs))
def r2o(r):
 for nm,va,vs,ptr,rs in secs:
  if va<=r<va+max(vs,rs):return ptr+(r-va)
 return None
text=[x for x in secs if x[0]=='.text'][0];va,vs,ptr,rs=text[1],text[2],text[3],text[4]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
# find indirect jmp/call [reg*4+disp32] in .text and validate table values in DLL image
cands=[]
for r in range(va,va+min(vs,rs)-8):
 o=ptr+(r-va)
 if b[o:o+2] not in (b'\xff\x24',b'\xff\x14'):continue
 ins=list(md.disasm(b[o:o+7],IB+r))
 if not ins:continue
 x=ins[0]
 if x.mnemonic not in ('jmp','call') or '*4' not in x.op_str:continue
 disp=struct.unpack_from('<I',b,o+3)[0]
 if disp<IB:continue
 # map disp VA to file offset
 dr=disp-IB;dof=r2o(dr)
 if dof is None:continue
 vals=[struct.unpack_from('<I',b,dof+j*4)[0] for j in range(40)]
 good=[v-IB for v in vals if IB+va<=v<IB+va+vs]
 if len(good)>=4:
  cands.append((r,dr,len(good),good[:10],x.op_str,x.mnemonic))
print('DLL indirect tables with valid text targets:',len(cands))
for c in cands[:300]:print(hex(c[0]),hex(c[1]),c[2],[hex(x) for x in c[3]],c[5],c[4])
json.dump(cands,open(r'D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOL-BATTLE-SERVER-APP-MSG-ENTRY-038\\evidence\\dll_indirect_tables.json','w'),indent=2)

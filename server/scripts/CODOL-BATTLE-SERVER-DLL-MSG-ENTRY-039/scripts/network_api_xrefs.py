import pefile,struct,capstone,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
# collect all string RVsAs from .rdata for WSA API names
import re
strs={}
for s in pe.sections:
 if s.Name.rstrip(b'\0').decode('latin1') not in ('.rdata','.idata2','.text'):continue
 base=s.PointerToRawData;data=b[base:base+s.SizeOfRawData]
 for m in re.finditer(rb'[A-Za-z_][A-Za-z0-9_@?]{2,60}\x00',data):
  st=m.group()[:-1]
  try:txt=st.decode('ascii')
  except:continue
  if any(k in txt.lower() for k in ['wsa','socket','recv','send','select','connect','bind','listen','accept','gethost','getaddr','net']):
   strs[IB+s.VirtualAddress+m.start()]=txt
print('candidate network strings',len(strs))
for va,txt in sorted(strs.items()):print(hex(va),hex(va-IB),txt)
# xrefs: find push imm32 / mov reg,imm32 of these VAs
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
print('\nXREFS')
for va,txt in sorted(strs.items()):
 pat=struct.pack('<I',va);hits=[];st=0
 while True:
  j=b.find(pat,st)
  if j<0:break
  r=pe.get_rva_from_offset(j)
  if r is not None:hits.append(r)
  st=j+1
 if hits:
  print(txt,hex(va),[hex(x) for x in hits[:20]])
  for r in hits[:4]:
   s=max(0,r-64);off=pe.get_offset_from_rva(s)
   print('  ctx @',hex(r))
   for i in md.disasm(b[off:off+160],IB+s):print(f'    {i.address-IB:08X} {i.bytes.hex():<18s} {i.mnemonic} {i.op_str}')

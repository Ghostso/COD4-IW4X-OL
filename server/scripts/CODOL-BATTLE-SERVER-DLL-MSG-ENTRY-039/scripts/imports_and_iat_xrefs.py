import pefile,struct,json,capstone
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
print('=== ALL IMPORTS (network-related and counts) ===')
for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
 dll=e.dll.decode(errors='replace')
 print('\nDLL',dll,'imports',len(e.imports))
 for imp in e.imports:
  nm=imp.name.decode() if imp.name else ('ord#'+str(imp.ordinal) if imp.ordinal else '?')
  show=any(k in dll.lower() for k in ['ws2','wsock']) or any(k in nm.lower() for k in ['socket','wsarecv','wsasend','recv','send','select','wsa','connect','bind','listen','accept','gethost','getaddr'])
  print(f'  {imp.address:#010x} {nm} hint={imp.hint}')
print('\n=== IAT/slot xref scan for ws2_32/wsock32 slots ===')
slots=[]
for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
 dll=e.dll.decode(errors='replace').lower()
 if 'ws2' in dll or 'wsock' in dll:
  for imp in e.imports:
   nm=imp.name.decode() if imp.name else None
   slots.append((imp.address,nm,dll))
print('slots',[(hex(a),n,d) for a,n,d in slots])
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
# xrefs are instructions with absolute disp32 to IAT slot OR FF15 [slot]
for slot,nm,dll in slots:
 pat=struct.pack('<I',IB+slot)
 hits=[];st=0
 while True:
  j=b.find(pat,st)
  if j<0:break
  r=pe.get_rva_from_offset(j)
  hits.append((j,r));st=j+1
 print('\nSLOT',nm,hex(slot),'hits',[(hex(o),hex(r)) for o,r in hits[:30]])
 for o,r in hits[:10]:
  s=max(0,r-80);e2=min(pe.OPTIONAL_HEADER.SizeOfImage,r+80)
  print('  --- xref rva',hex(r),'---')
  oo=pe.get_offset_from_rva(s)
  for i in md.disasm(b[oo:oo+(e2-s)],IB+s):print(f'    {i.address-IB:08X} {i.bytes.hex():<20s} {i.mnemonic} {i.op_str}')

import pefile,struct,capstone,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
# memory image with relocations applied (conceptually: reloc stores pref VA; mapping table from VA to RVA)
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def off2rva(o):
 for s in pe.sections:
  if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:return s.VirtualAddress+(o-s.PointerToRawData)
 return None
def rva2off(r):
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+(r-s.VirtualAddress)
 return None
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<18s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n=240):
 o=rva2off(rva)
 if o is None:return []
 return list(md.disasm(b[o:o+n],IB+rva))
# collect strings and reloc-backed pointer references to their VAs
patterns=[b'WKNet_',b'[KernelBind]',b'[KernelConnect]',b'[KernelDisconnect]',b'SendPacket',b'GetNewReport',b'SetUserEventNotify',b'GetProcessModList']
for pat in patterns:
 print('\n########',pat,'########')
 st=0;found=0;seen=set()
 while True:
  j=b.find(pat,st)
  if j<0:break
  r=off2rva(j)
  if r is None:st=j+1;continue
  va=IB+r
  if va not in seen:
   seen.add(va);print(' string rva',hex(r),'va',hex(va),'ctx',b[j:j+64])
   # find reloc entries whose stored addend equals va? inspect all .data/.rdata pointers
   ptr=struct.pack('<I',va);hits=[];st2=0
   while True:
    k=b.find(ptr,st2)
    if k<0:break
    rr=off2rva(k)
    if rr is not None:
     # verify reloc entry exists near rr
     has=any(rb.struct.VirtualAddress<=rr<rb.struct.VirtualAddress+rb.struct.SizeOfBlock for rb in pe.DIRECTORY_ENTRY_BASERELOC)
     hits.append((k,rr,has))
    st2=k+1
   print('  raw pointer hits',[(hex(o),hex(rr),has) for o,rr,has in hits[:20]])
  st=j+1;found+=1
  if found>=8:break
# list reloc entries that point into .text and whose target function begins with prologue; gather candidates near socket calls
text=[s for s in pe.sections if s.Name.startswith(b'.text')][0]
# search for FF15 call absolute IAT patterns; resolve targets to import names by scanning .idata2 thunk strings
print('\n=== FF15 absolute call targets in .text (first 300 unique) ===')
targets={}
for r in range(text.VirtualAddress,text.VirtualAddress+text.Misc_VirtualSize-6):
 o=rva2off(r)
 if o is None:continue
 if b[o:o+2]==b'\xff\x15':
  slot=struct.unpack_from('<I',b,o+2)[0]
  targets[slot]=targets.get(slot,0)+1
for slot,c in sorted(targets.items(),key=lambda x:-x[1])[:120]:
 print(hex(slot),c)

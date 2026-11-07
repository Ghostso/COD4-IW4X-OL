import pefile,struct,capstone,re,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def off2rva(o):
 for s in pe.sections:
  if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:return s.VirtualAddress+(o-s.PointerToRawData)
 return None
def rva2off(r):
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+(r-s.VirtualAddress)
 return None
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<20s} {i.mnemonic} {i.op_str}".rstrip()
def xrefs(va):
 pat=struct.pack('<I',va);out=[];st=0
 while True:
  j=b.find(pat,st)
  if j<0:break
  r=off2rva(j)
  if r is not None:out.append(r)
  st=j+1
 return out
def context(r,before=96,after=220):
 s=max(0,r-before);o=rva2off(s)
 if o is None:return []
 return list(md.disasm(b[o:o+after+before],IB+s))
# find strings of interest and their VAs
patterns=[b'WKNet_',b'[KernelBind]',b'[KernelConnect]',b'SendPacket',b'RecvPacket',b'ReceivePacket',b'OnPacket',b'ParsePacket',b'netchan',b'NetChan',b'gamestateupdate',b'configstring']
print('=== string VAs and xrefs ===')
for pat in patterns:
 print('\nPATTERN',pat)
 st=0;found=0
 while True:
  j=b.find(pat,st)
  if j<0:break
  r=off2rva(j)
  if r is None:st=j+1;continue
  va=IB+r
  print(' string off',hex(j),'rva',hex(r),'va',hex(va),'ctx',b[j:j+80])
  for x in xrefs(va)[:12]:
   print('  xref rva',hex(x))
   for i in context(x):print('   ',fmt(i))
  st=j+1;found+=1
  if found>=6:break

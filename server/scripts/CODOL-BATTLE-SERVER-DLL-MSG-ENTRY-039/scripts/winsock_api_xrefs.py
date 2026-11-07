import pefile,struct,capstone,re,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def rva2off(r):
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+(r-s.VirtualAddress)
 return None
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<18s} {i.mnemonic} {i.op_str}".rstrip()
def off2rva(o):
 for s in pe.sections:
  if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:return s.VirtualAddress+(o-s.PointerToRawData)
 return None
def imm_xrefs(va):
 pat=struct.pack('<I',va);out=[];st=0
 while True:
  j=b.find(pat,st)
  if j<0:break
  r=off2rva(j)
  if r is not None:out.append(r)
  st=j+1
 return out
# find canonical API names in .rdata and their references
names=[b'WSAStartup',b'WSASocketW',b'WSARecv',b'WSASend',b'WSARecvFrom',b'WSASendTo',b'recvfrom',b'sendto',b'recv',b'send',b'select',b'ioctlsocket',b'closesocket',b'WSAEventSelect',b'WSAEnumNetworkEvents']
for nm in names:
 print('\n===',nm.decode(),'===')
 st=0;found=0
 while True:
  j=b.find(nm,st)
  if j<0:break
  r=off2rva(j);va=IB+r if r is not None else None
  if va is not None and r>=0x743000 and r<0x9af000:
   xr=imm_xrefs(va)
   if xr:
    print(' str rva',hex(r),'va',hex(va),'xrefs',[hex(x) for x in xr[:12]])
    for x in xr[:6]:
     print('  ctx',hex(x))
     s=max(0,x-80);o=rva2off(s)
     for i in md.disasm(b[o:o+240],IB+s):print('   ',fmt(i))
   found+=1
  st=j+1
  if found>=4:break

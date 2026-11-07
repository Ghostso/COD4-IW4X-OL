import pefile,struct,re,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=True);IB=pe.OPTIONAL_HEADER.ImageBase
def sec_of_off(o):
 for s in pe.sections:
  if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:return s.Name.rstrip(b'\0').decode('latin1')
 return '?'
def off2rva(o):
 for s in pe.sections:
  if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:return s.VirtualAddress+(o-s.PointerToRawData)
 return None
def dis(rva,n=300):
 import capstone;md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
 o=pe.get_offset_from_rva(rva)
 if o is None:return []
 return list(md.disasm(b[o:o+n],IB+rva))
needles=[b'ws2_32',b'wsock32',b'WSAStartup',b'WS2_32',b'socket',b'recvfrom',b'sendto',b'closesocket',b'select',b'ioctlsocket',b'gethostbyname',b'getaddrinfo',b'WSARecv',b'WSASend',b'connect',b'bind',b'listen',b'accept',b'udp',b'UDP',b'netchan',b'NetChan',b'NetChannel',b'NETCHAN']
for nd in needles:
 hits=[];st=0
 while True:
  j=b.lower().find(nd.lower(),st)
  if j<0:break
  hits.append(j);st=j+1
  if len(hits)>=30:break
 if hits:
  print('\nNEEDLE',nd.decode(errors='replace'),'count(first30)',len(hits))
  for j in hits:print('  off',hex(j),'sec',sec_of_off(j),'rva',hex(off2rva(j)) if off2rva(j) is not None else None,'ctx',b[max(0,j-20):j+80])

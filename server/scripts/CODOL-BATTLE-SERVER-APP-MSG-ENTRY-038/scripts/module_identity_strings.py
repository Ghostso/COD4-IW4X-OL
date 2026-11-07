import struct,hashlib,json,re
base=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL"
paths={'exe':base+r"\\codoMP_client_shipRetail.exe",'dll':base+r"\\codoMP_client_shipRetailBase.dll",'image':r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"}
needles=[b'netchan',b'gamestateupdate',b'challengeResponse',b'connectResponse',b'configstring',b'snapshot',b'entity',b'packet',b'opcode',b'heartbeat',b'getchallenge',b'cancelConnect']
for name,p in paths.items():
 b=open(p,'rb').read()
 print('\n====',name,p,len(b),hashlib.sha256(b).hexdigest())
 off=struct.unpack_from('<I',b,0x3c)[0] if b[:2]==b'MZ' else 0
 if b[off:off+4]==b'PE\0\0':
  coff=off+4; machine,nsec,tstamp=struct.unpack_from('<HHI',b,coff)
  opt=coff+20; magic=struct.unpack_from('<H',b,opt)[0]
  ib=struct.unpack_from('<I',b,opt+28)[0] if magic==0x10b else struct.unpack_from('<Q',b,opt+24)[0]
  entry=struct.unpack_from('<I',b,opt+16)[0];sizeimage=struct.unpack_from('<I',b,opt+56)[0]
  print('PE machine',hex(machine),'nsec',nsec,'tstamp',hex(tstamp),'imagebase',hex(ib),'entry',hex(entry),'sizeimage',hex(sizeimage))
  sec=opt+struct.unpack_from('<H',b,coff+16)[0]
  for i in range(nsec):
   q=sec+i*40;nm=b[q:q+8].split(b'\0')[0].decode('latin1');vs,va,rs,ptr=struct.unpack_from('<IIII',b,q+8)
   print(f' {nm:8s} VA={va:#x} VS={vs:#x} RAW={ptr:#x} RS={rs:#x}')
 for nd in needles:
  hits=[];start=0
  while True:
   j=b.lower().find(nd.lower(),start)
   if j<0:break
   hits.append(j);start=j+1
   if len(hits)>=8:break
  if hits:print(' needle',nd.decode(),[hex(x) for x in hits])

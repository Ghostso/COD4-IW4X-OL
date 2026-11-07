import struct,capstone,hashlib,json,re
p=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(p,'rb').read();IB=0x10000000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def rva2off(rva):
 off=0x3c;e=struct.unpack_from('<I',b,off)[0];coff=e+4;nsec=struct.unpack_from('<H',b,coff+2)[0];optsize=struct.unpack_from('<H',b,coff+16)[0];sec=coff+20+optsize
 for i in range(nsec):
  q=sec+i*40;vs,va,rs,ptr=struct.unpack_from('<IIII',b,q+8)
  if va<=rva<va+max(vs,rs):return ptr+(rva-va)
 return None
def dis(rva,n=128):
 o=rva2off(rva)
 if o is None:return []
 return list(md.disasm(b[o:o+n],IB+rva))
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
# find strings for app message/protocol keywords and their xrefs
needles=[b'opcode',b'netchan',b'Netchan',b'gamestate',b'configstring',b'snapshot',b'parseServerMessage',b'PacketEntities',b'packetEntities',b'msg_',b'CL_']
print('RVA mapping samples:')
for s in needles:
 start=0;hits=[]
 while True:
  j=b.lower().find(s.lower(),start)
  if j<0:break
  # classify PE section
  secname=None
  e=struct.unpack_from('<I',b,0x3c)[0];coff=e+4;nsec=struct.unpack_from('<H',b,coff+2)[0];optsize=struct.unpack_from('<H',b,coff+16)[0];sec=coff+20+optsize
  for i in range(nsec):
   q=sec+i*40;vs,va,rs,ptr=struct.unpack_from('<IIII',b,q+8)
   if ptr<=j<ptr+rs:secname=(b[q:q+8].split(b'\0')[0].decode('latin1'),va+(j-ptr));break
  hits.append((j,secname,b[j:j+80]))
  start=j+1
  if len(hits)>=6:break
 print('\n',s, 'count(first6)',len(hits))
 for h in hits:print('  ',hex(h[0]),h[1],h[2])
# Search for string reference helper: scan push imm32 of VA for opcode/netchan strings
print('\nXREFS to selected string VAs:')
for s in [b'opcode',b'netchan',b'gamestate',b'configstring',b'snapshot']:
 # take first string VA in rdata
 idx=b.lower().find(s.lower())
 if idx<0:continue
 # compute rva
 va=None
 e=struct.unpack_from('<I',b,0x3c)[0];coff=e+4;nsec=struct.unpack_from('<H',b,coff+2)[0];optsize=struct.unpack_from('<H',b,coff+16)[0];sec=coff+20+optsize
 for i in range(nsec):
  q=sec+i*40;vs,vaa,rs,ptr=struct.unpack_from('<IIII',b,q+8)
  if ptr<=idx<ptr+rs:va=IB+vaa+(idx-ptr);break
 if va is None:continue
 pat=struct.pack('<I',va);hits=[];st=0
 while True:
  j=b.find(pat,st)
  if j<0:break
  hits.append(j);st=j+1
  if len(hits)>=20:break
 print(s,hex(va),'xrefs',[hex(x) for x in hits[:12]])

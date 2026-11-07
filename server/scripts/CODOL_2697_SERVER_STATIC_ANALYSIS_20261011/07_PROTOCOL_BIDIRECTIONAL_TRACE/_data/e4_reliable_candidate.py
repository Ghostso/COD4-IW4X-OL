import sys,os,struct,bisect
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c,c_xref as x
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
im=c.load(c.CLIENT_CAND); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for va in [0xCB8378,0xCB69D4,0xCB83E0,0xCB83E8,0xCB3994,0xCA204A,0xCC6334,0xCB6514,0xCA2340]:
 r=va-im.ib; print('STR',hex(va),'rva',hex(r),'sec',im.sec_of(r),'::',repr(im.cstr(r,256)))
# full A2D90..A30A0
print('\nFUNCTION REGION A2D90-A30A0')
for ins in im.disasm(0xA2D90,0xA30A0):
 print(' %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))
# direct callers for candidate function starts, normalized VA
for t in [0xA2D90,0xA2DF0,0xA2E50,0xA2F80,0xA3050,0xA2E50+im.ib,0xA2D90+im.ib]:
 arr=[]; tar=im.ib+t if t<im.ib else t
 for ins in im.disasm(0x1000,0x7ADA00):
  if ins.mnemonic=='call':
   try:d=int(ins.op_str,16)
   except:continue
   if d==tar: arr.append(ins.address-im.ib)
 print('calls to',hex(t),'->',[hex(a) for a in arr])
# xrefs to error/data addresses, including pointers
for va in [0xCB8378,0xCB69D4,0xCB83E0,0xCB83E8,0xCB3994,0xCA204A,0xCC6334,0xCB6514,0xCA2340]:
 pat=struct.pack('<I',va); a=[]; s=0
 while True:
  j=im.data.find(pat,s)
  if j<0:break
  sec=None
  for nm,v0,vs,pt,rs in im.sections:
   if rs and pt<=j<pt+rs: sec=(nm,v0+(j-pt));break
  a.append((j,sec));s=j+1
 print('XREF',hex(va),[(hex(o),hex(rv) if rv else None,nm if rv else None) for o,(nm,rv) in [(o,sec) for o,sec in a]][:40])
# near strings dump
for center in [0x8B82C0,0x8B8300,0x8B8340,0x8B8380,0x8B83C0,0x8B83E0]:
 print('\nDUMP .rdata',hex(center))
 print(repr(im.read_rva(center,0xC0)))
# function start / prologue listing in region based on e8 calls and int3 boundaries
print('\nPROLOGUE CANDIDATES A2000-A3500')
for r in range(0xA2000,0xA3500):
 if im.data[im.sec_of(r)[3]+r-im.sec_of(r)[1]:im.sec_of(r)[3]+r-im.sec_of(r)[1]+3]==b'\x55\x8b\xec':
  print(hex(r))

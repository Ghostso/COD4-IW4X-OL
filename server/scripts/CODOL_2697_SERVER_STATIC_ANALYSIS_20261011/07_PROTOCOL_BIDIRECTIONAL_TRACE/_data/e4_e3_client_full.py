import sys,os,struct
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load(c.CLIENT_CAND)
def dis(r,n):
 print('\nDIS',hex(r),'count',n)
 for ins in im.disasm(r,count=n): print(' %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))
dis(0xA2E50,220)
# raw bytes around 0xa2e40..0xa3080
for r in [0xA2E40,0xA2E50,0xA2F00,0xA2F70,0xA2F80,0xA3000,0xA3060]:
 s=im.sec_of(r); f=s[3]+r-s[1]; print('BYTES',hex(r),hex(f),im.data[f:f+128].hex())
# search exact byte pattern of function prologue and compare all candidates
pat=bytes.fromhex('558bec81ec44040000a1f06dd10033c58945fc53568bf18b4e188b461c034e14')
hits=[];s=0
while True:
 j=im.data.find(pat,s)
 if j<0:break
 for nm,va,vs,pt,rs in im.sections:
  if rs and pt<=j<pt+rs: hits.append((va+j-pt,j));break
 s=j+1
print('exact prologue hits',[(hex(a),hex(o)) for a,o in hits])

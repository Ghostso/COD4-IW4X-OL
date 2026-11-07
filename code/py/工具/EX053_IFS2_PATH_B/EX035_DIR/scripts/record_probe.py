import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; raw0=0x594000; va0=0x8A8000
def rd(va):return struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
# test the record stride hypothesis: value sequence base and every slot offset
for stride in [8,12,16,20,24,32,40,64]:
 ok=tot=0; starts=collections.Counter()
 for va in range(0xCA8000,0xCA93D0,stride):
  v=rd(va); tot+=1
  if IB<=v<0xEA59000:ok+=1
  starts[(va-0xCA8000)%stride]+=1
 print('stride',stride,'start-position pointer ratio',ok,tot,round(ok/tot,3))
# fixed-record candidates where value fields align and zeros in remainder
print('\nrecord probes 8/16/20/32')
for stride in [8,16,20,32]:
 print('stride',stride)
 for rel in range(0,stride,4):
  vals=[rd(x+rel) for x in range(0xCA8D10,0xCA93D0,stride)]
  print(' rel',rel,'nonzero',sum(v!=0 for v in vals),'ptr',sum(IB<=v<0xEA59000 for v in vals),'zero',sum(v==0 for v in vals))

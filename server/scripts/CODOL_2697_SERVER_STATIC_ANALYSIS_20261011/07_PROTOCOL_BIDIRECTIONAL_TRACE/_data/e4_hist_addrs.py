import sys,os,struct
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load(c.CLIENT_CAND)
for va in [0x02DF7D90,0x0057A300,0x005850B0,0x02DF7D90-0x400000]:
 rva=va-im.ib if va>=im.ib else va
 print('\nADDR',hex(va),'rva',hex(rva),'sec',im.sec_of(rva))
 if im.sec_of(rva):
  print('bytes',im.read_rva(rva,64).hex())
  c.show(im,rva,rva+0x160)

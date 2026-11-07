import sys, os, struct, json
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c, c_xref as x
im=c.load(c.CLIENT_CAND)
print('sections')
for s in im.sections: print(s)
print('\nDISASM 0xA2CE0-0xA2F20')
c.show(im,0xA2CE0,0xA2F20)
tbl=x.text_call_targets(im)
for badr in [0xA2D90,0x5AC1D0,0x63CB50,0x63C7F0,0x5B1F20]:
 print('CALLERS %X:'%badr,[hex(v) for v in x.callers(im,badr,tbl)])
for label,rva in [('gs1',0x56893),('gs2',0xA2994),('gs3',0x1F14F7)]:
 print('\n===',label,hex(rva),'===')
 c.show(im,max(0,rva-0x80),rva+0x140)
print('\nSTRING LOCATIONS')
for needle in [b'gamestateupdate %d',b'EXE_CONFIGSTRINGMISMATCH',b'UNEXPECTED_EOF',b'getchallenge',b'connect',b'serverCommand',b'configstring',b'snapshot']:
 print(needle,x.find_strings(im,needle)[:20])
for needle in [b'gamestateupdate %d',b'EXE_CONFIGSTRINGMISMATCH',b'UNEXPECTED_EOF']:
 for off,rva in x.find_strings(im,needle):
  print(needle.decode(),'off',hex(off),'rva',hex(rva),'sec',im.sec_of(rva)[0])
  for patt in [struct.pack('<I',im.ib+rva),struct.pack('<I',rva)]:
   a=[]; start=0
   while True:
    j=im.data.find(patt,start)
    if j<0: break
    a.append(j); start=j+1
   print(' patt',patt.hex(),'fileoffs',[hex(v) for v in a[:20]],'count',len(a))

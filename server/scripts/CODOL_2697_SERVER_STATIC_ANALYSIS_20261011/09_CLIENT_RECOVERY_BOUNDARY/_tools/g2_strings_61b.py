
import sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
seen=set();out=[]
for rva in range(0x83B700,0x83C100):
 s=im.cstr(rva,200)
 if not s: continue
 printable=sum(1 for ch in s if 32<=ord(ch)<127 or ch in '\r\n\t')
 if len(s)>=3 and printable/len(s)>0.8:
  # avoid suffixes by only print if previous byte is NUL
  if rva==0 or im.read_rva(rva-1,1)==b'\0':
   if s not in seen: out.append('%#x %r'%(rva,s)); seen.add(s)
print('\n'.join(out))

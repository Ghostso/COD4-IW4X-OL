
import sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load();out=[];seen=set()
for rva in range(0x88F000,0x89A000):
 s=im.cstr(rva,200)
 if not s or len(s)<4:continue
 printable=sum(1 for ch in s if 32<=ord(ch)<127 or ch in '\r\n\t')
 if printable/len(s)<0.85:continue
 prev=im.read_rva(rva-1,1)
 if prev!=b'\0' and rva!=0x88F000:continue
 if s in seen:continue
 seen.add(s);out.append('%#x %s'%(rva,repr(s)))
print('\n'.join(out[:500]))

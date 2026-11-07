
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
# raw bytes at candidate RVAs
for rva in (0x1ac1d0,0x5ac1d0,0x1aca10,0x5aca10,0x1acb00,0x5acb00,0x1ac670,0x5ac670,0x1ac980,0x5ac980,0x1ac8c0,0x44c8c0):
    b=im.read_rva(rva,24)
    lines.append('%#x %s' % (rva,b.hex()))
open(os.path.join(OUT,'f_raw_helper_bytes.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))

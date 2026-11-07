import sys, os
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
out=[]
for i in im.disasm(0xA2E50, end_rva=0xA3000):
    out.append('%08x %-20s %-8s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data\f_a2e50_full.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
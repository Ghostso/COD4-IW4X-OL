import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import xref
b=xref.load()
for t in (0x861F8,0x86248,0x862DA,0x8960D,0x89E9C,0x540133):
    print(hex(t), [hex(x[0]) for x in xref.call_xrefs(b,{t})])

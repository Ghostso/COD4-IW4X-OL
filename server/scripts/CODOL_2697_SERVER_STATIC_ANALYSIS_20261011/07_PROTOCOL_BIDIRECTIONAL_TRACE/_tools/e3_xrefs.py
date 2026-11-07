import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import xref
b=xref.load()
for t in (0x860DE,0x8612E,0x85D32,0x85CFB,0x486217,0x48622B,0x4862AC,0x86B06,0x87073):
    print(hex(t), "calls", [hex(x[0]) for x in xref.call_xrefs(b,{t})])
    print(hex(t), "abs", [(x[0],hex(x[1])) for x in xref.abs_va_refs(b,{0x400000+t,t})])

import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import xref
b=xref.load()
for t in (0xA4FA0,0xA4860,0xA26EB,0xBEE00,0xBE946,0x86B06,0x86F7D,0x8743C,0x8A9F1,0x84158,0x89081):
    print(hex(t), [hex(x[0]) for x in xref.call_xrefs(b,{t})])

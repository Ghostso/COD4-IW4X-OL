import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e
b = e.load_bin(e.SRV, e.DATA + r"\syms_NEW.json")
for nm, rva, end in [("_CODOL_Server2697ResourceSource",0x4c3020,0x4c3130),
                     ("_CODOL_Server2697Registration",0x4c3026,0x4c3130),
                     ("_CODOL_SetTarget2697ServerResources",0xc311b,0xc3360),
                     ("_CODOL_Server2697ResourceSource(alt?)",0x4c3020,0x4c3026)]:
    print("#### %s  RVA 0x%X"%(nm,rva))
    e.show(b, rva, end_rva=end)
    print()

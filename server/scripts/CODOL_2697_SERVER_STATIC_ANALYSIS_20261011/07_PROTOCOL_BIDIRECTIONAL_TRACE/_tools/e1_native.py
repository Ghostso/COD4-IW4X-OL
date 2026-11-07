import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e
b = e.load_bin(e.SRV, e.DATA + r"\syms_NEW.json")
print("### _CODOL2697_WriteNativeGamestate  RVA 0xA3DAB..0xA3EA0")
e.show(b, 0xa3dab, end_rva=0xa3ea0)

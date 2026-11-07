import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e
b=e.load_bin(e.SRV,e.DATA+r"\syms_NEW.json")
print("=== UpdateServerCommandsToClient 0x861F8 ===")
e.show(b,0x861F8,0x86320)

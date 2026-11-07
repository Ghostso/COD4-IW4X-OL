import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e
b=e.load_bin(e.SRV,e.DATA+r"\syms_NEW.json")
for rva in (0x3B98E0,0x3B98F7,0x3B98FC):
    print(hex(rva), repr(b.cstr(rva,128)))
print("=== ProfileCommandBytes 0x85D32 ===")
e.show(b,0x85D32,0x85E80)

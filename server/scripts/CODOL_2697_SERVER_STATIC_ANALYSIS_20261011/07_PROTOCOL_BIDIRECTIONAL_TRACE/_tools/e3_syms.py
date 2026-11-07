import sys,json
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e
b=e.load_bin(e.SRV,e.DATA+r"\syms_NEW.json")
for name in ["_SV_WriteReliableCommand","_SV_ProfileCommand2697","_CODOL2697_ProfileCommandBytes","_SV_CodolLinkParent","_SV_UpdateServerCommandsToClient","_SV_UpdateServerCommandsToClientRecover"]:
    s=b.syms.get(name)
    print(name, s and (hex(s["rva"]), s.get("value")))

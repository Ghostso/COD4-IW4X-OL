import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C)
print("=== client: DEADBEEF + tags + Demonware markers ===")
for pat in [bytes.fromhex("efbeadde"), b"DEADBEEF", b"bdLobbyConnection", b"bdLobby", b"dwLobby", b"dwRoom", b"bdBase64", b"getMessageToDispatch", b"service102", b"bdCore", b"bdCommon"]:
    print("  %-24s %d"%(pat.decode('latin1','replace'), im.d.count(pat)))
print()
# also check the 2697 server + bridge DLLs for DEADBEEF
for label,p in [("dedrun",r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"),
                ("room_dll",r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll"),
                ("loopback_dll",r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll"),
                ("guard_exe",r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_loopback_guard.exe")]:
    m=Img(p)
    hits=[k for k in (b"DEADBEEF",bytes.fromhex("efbeadde"),b"bdLobby",b"dwLobby",b"dwRoom",b"bdBase64") if k in m.d]
    print("  %-14s markers=%s"%(label,hits))

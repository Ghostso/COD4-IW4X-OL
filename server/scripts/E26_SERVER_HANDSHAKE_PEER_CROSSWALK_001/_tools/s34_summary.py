import sys, json
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
# summarize the whole server-side handshake family with symbol addresses
j=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json",encoding='utf-8'))
syms={s['name']:s['rva'] for s in j['symbols'] if isinstance(s,dict)}
names=["_SV_ReadPackets","_SV_PacketEvent","_SV_ConnectionlessPacket","_SV_DirectConnect",
       "_SV_Netchan_Decode","_SV_Netchan_Encode","_SV_Netchan_Transmit","_SV_Netchan_TransmitNextFragment",
       "_Netchan_Setup","_Netchan_Process","_Netchan_Transmit","_Netchan_TransmitNextFragment",
       "_SV_ExecuteClientMessage","_SV_UserMove","_SV_ClientCommand","_SV_ExecuteClientCommand",
       "_CODOL_HandshakeClear","_CODOL_HandshakeInit","_CODOL_HandshakeCookie",
       "_CODOL_WriteChallengeResponse","_CODOL_NetchanProcess","_CODOL_NetchanTransmit","_CODOL_NetchanSubmit",
       "_CODOL_NetworkInit","_CODOL_NetworkAdmission","_CODOL_NetworkAuthenticated","_CODOL_NetworkSessionReady",
       "_CODOL_NetworkSend","_CODOL_NetworkReceive","_CODOL_ReadClientCommand","_CODOL_MsgReadInit","_CODOL_ReadByte","_CODOL_ReadShort","_CODOL_ReadLong"]
for n in names:
    print("  %-32s %s"%(n, ("RVA %06X VA %08X"%(syms[n],IB+syms[n])) if n in syms else "NOT FOUND"))

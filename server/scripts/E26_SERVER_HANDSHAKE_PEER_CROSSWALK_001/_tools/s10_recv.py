import json
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(p,encoding='utf-8'))
syms=[s for s in j['symbols'] if isinstance(s,dict)]
for kw in ['ExecuteClientMessage','ClientCommand','Connectionless','SV_DirectConnect','SV_GetPacket','SV_ReadPackets','SV_Netchan_','SV_Process','SV_UserMove','SV_ClientThink','ClientPacket','RecvFrom','SV_Frame','SV_PacketEvent']:
    hits=[s for s in syms if kw.lower() in (s.get('name') or '').lower()]
    print("=== %s : %d ==="%(kw,len(hits)))
    for h in hits[:14]: print("   %08X %s"%(h['rva'],h['name']))

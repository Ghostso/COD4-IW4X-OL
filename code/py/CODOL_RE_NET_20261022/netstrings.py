import pefile, re
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
secs=[(s.VirtualAddress,s.PointerToRawData,s.SizeOfRawData,s.Name.rstrip(b"\0").decode()) for s in pe.sections]
def off2rva(off):
    for va,ra,rs,nm in secs:
        if ra<=off<ra+rs: return va+(off-ra),nm
    return None,None
pat=re.compile(rb'[\x20-\x7e]{5,}')
strs=[]
for m in pat.finditer(d):
    rva,nm=off2rva(m.start())
    if rva: strs.append((rva,m.group().decode('ascii'),nm))
print('strings',len(strs))
queries=['failed to load WS2_32','NET_','Netchan','netchan','CL_','clc_','svc_','CLC_','SVC_','configstring','ConfigString','CONFIGSTRING','gamestate','Gamestate','GAMESTATE','snapshot','Snapshot','SNAPSHOT','usercmd','Usercmd','UserCmd','USERCMD','ClientConnect','SV_','CL_Parse','CL_Send','CL_Connect','CL_Disconnect','SV_Send','SV_Client','challenge','challengeResponse','getchallenge','connectResponse','authInfo','dw_auth','dwauth','iips','IIPS','lobby','Lobby','matchmaking','Matchmaking','CODOL','codol','shipRetail','Base.dll','cl_packet','sv_packet']
for q in queries:
    ms=[x for x in strs if q in x[1]]
    if ms:
        print('\n== %s : %d' % (q,len(ms)))
        for rva,s,nm in ms[:30]:
            print('   %08x %-7s %s' % (rva,nm,s[:150]))

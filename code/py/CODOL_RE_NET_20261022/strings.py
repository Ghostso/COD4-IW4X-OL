import pefile, re, os
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
secs=[]
for s in pe.sections:
    nm=s.Name.rstrip(b"\0").decode()
    secs.append((s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData, nm))
def off2rva(off):
    for va,ra,rs,nm in secs:
        if ra<=off<ra+rs: return va+(off-ra), nm
    return None,None
# ascii strings >=6
pat=re.compile(rb'[\x20-\x7e]{6,}')
hits=[]
for m in pat.finditer(d):
    s=m.group().decode('ascii')
    hits.append((m.start(), s))
print('total ascii strings', len(hits))
keys=['ws2_32','WS2_32','winhttp','WinHttp','WINHTTP','WSAStartup','getaddrinfo','InternetOpen','connect','Connect','sendto','recvfrom','socket','Socket','netchan','NET_','clc_','svc_','CL_','SV_','auth','Auth','AUTH','iips','IIPS','lobby','Lobby','gamestate','GAMESTATE','configstring','ConfigString','dwauth','Tencent','tencent','qq.com','codol','CODOL','dll']
for k in keys:
    ms=[(o,s) for o,s in hits if k in s]
    if ms:
        print('\n==',k,len(ms))
        for o,s in ms[:40]:
            rva,nm=off2rva(o)
            print('  %#010x %-8s %s' % (rva if rva else 0, nm, s[:160]))

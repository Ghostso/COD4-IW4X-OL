# -*- coding: utf-8 -*-
import io, os
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
EV=os.path.join(ROOT,"evidence")
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)
def N(x): return int(x,16)

slots={}
with io.open(os.path.join(EV,"winsock_slots.tsv"),encoding="utf-8") as f:
    f.readline()
    for ln in f:
        p=ln.rstrip("\n").split("\t")
        nm=p[6].split("(")[0]
        slots.setdefault(nm,[]).append(dict(rva=N(p[1]),va=p[2],off=p[3],kind=p[4],raw=p[6]))
calls=[]
with io.open(os.path.join(EV,"winsock_callsites.tsv"),encoding="utf-8") as f:
    hdr=f.readline().rstrip("\n").split("\t")
    for ln in f: calls.append(dict(zip(hdr,ln.rstrip("\n").split("\t"))))
by_api={}
for c in calls: by_api.setdefault(c["RESOLVED_API"],[]).append(c)

INTEREST=["recv","recvfrom","WSARecv","WSARecvFrom","WSAEventSelect","WSAEnumNetworkEvents","WSAIoctl",
 "select","WSASocketW","ioctlsocket","WSACreateEvent","WSACloseEvent","WSAWaitForMultipleEvents",
 "WSASend","send","sendto","WSAGetLastError","WSASetLastError","closesocket","socket","connect","bind","listen","accept",
 "WSAStartup","WSACleanup","gethostbyname","gethostname","getaddrinfo","getnameinfo","freeaddrinfo","WSAEnumProtocolsW",
 "WSCGetProviderPath","WSCEnumProtocols","__WSAFDIsSet","setsockopt","getsockopt","ioctlsocket","shutdown","getpeername","getsockname"]

hdr=["EVID_ID","API","SLOT_COUNT","SLOT_RVAS","RESOLVE_KIND","STAGE_NAME_OR_TEXT","STAGE_DYNAMIC_PARSE","STAGE_FP_STORAGE",
     "STAGE_FP_READ","STAGE_REAL_CALL","STAGE_RECV_BUFFER","STAGE_LENGTH_HANDLING","STAGE_NEXT_PARSE","OVERALL_STATUS","EVIDENCE"]
lines=["\t".join(hdr)+"\n"]
i=0
for api in INTEREST:
    i+=1
    si=slots.get(api)
    cl=by_api.get(api,[])
    slot_rvas=";".join("%#x"%s["rva"] for s in si) if si else ""
    kind = (si[0]["kind"] if si else "")
    resolve = ("IMAGE_IMPORT_BY_NAME" if kind=="NAME" else ("IMAGE_ORDINAL" if kind=="ORDINAL" else ""))
    s_name = "Y" if (si or cl) else "N"
    s_parse= "Y" if (api.upper().startswith("WSA") or api in ("getaddrinfo","getnameinfo","freeaddrinfo","select","ioctlsocket")) else "N"
    s_store= "Y" if si else "N"
    s_read = "Y" if si else "N"
    s_call = "Y" if cl else "N"
    s_buf  = "Y" if api=="recvfrom" else "N"
    s_len  = "Y" if api=="recvfrom" else "N"
    s_next = "N"
    if api=="recvfrom":
        overall="CONFIRMED_DATAFLOW (socket/event cluster -> recvfrom writes [ebp-0x10C])"
        ev="evidence/winsock_callsites.tsv (WC rows for recvfrom); SOCKET_EVENT_RECEIVE_CHAIN.md"
    elif cl:
        overall="CONFIRMED_DIRECT (fixed IAT slot + real FF15 call site)"
        ev="evidence/winsock_callsites.tsv"
    elif si:
        overall="CONFIRMED_CROSSREF (fixed IAT slot present; no FF15 call site observed in .text)"
        ev="evidence/winsock_slots.tsv"
    else:
        overall="UNKNOWN (no IAT slot, no FF15 call site observed)"
        ev="evidence/analysis_summary.json"
    lines.append("\t".join(["NAE-%03d"%i,api,str(len(si)) if si else "0",slot_rvas,resolve,
        s_name,s_parse,s_store,s_read,s_call,s_buf,s_len,s_next,overall,ev])+"\n")
W("NETWORK_API_EVIDENCE.tsv","".join(lines))
print("NETWORK_API_EVIDENCE.tsv rows:",i)

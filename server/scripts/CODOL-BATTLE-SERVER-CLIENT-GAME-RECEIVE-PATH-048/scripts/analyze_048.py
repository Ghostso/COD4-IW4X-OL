# -*- coding: utf-8 -*-
"""analyze_048.py - single reproducible pass that regenerates the 048 evidence.

Read-only w.r.t. the client. Writes only under evidence/.
Run:  python scripts\analyze_048.py
"""
import os, sys, json, struct, bisect, collections
sys.stdout.reconfigure(encoding="utf-8")
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import importlib.util
spec = importlib.util.spec_from_file_location("h048", os.path.join(_here, "048_harness.py"))
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)

IB=H.IB; IMG=H._img; LEN=len(IMG); LO,HI=0x1000,0x8A689A
IAT=H.ws2_iat_map()
OUT=os.path.join(H.TASK,"evidence")
os.makedirs(OUT, exist_ok=True)

def plausible_entry(t):
    if not (LO<=t<LEN-3): return False
    if IMG[t]==0x55 and IMG[t+1]==0x8B and IMG[t+2]==0xEC: return True
    if IMG[t] in (0x83,0x81) and IMG[t+1]==0xEC: return True
    if IMG[t]==0x6A and IMG[t+1]==0xFF: return True
    if t>=3 and IMG[t-3:t]==b"\xCC\xCC\xCC": return True
    if t>=1 and IMG[t-1] in (0xCC,0xC3): return True
    if t>=2 and IMG[t-2]==0xC2: return True
    return False

def build_call_sites():
    calls=[]
    for i in range(LO,HI-5):
        b=IMG[i]
        if b in (0xE8,0xE9):
            rel=struct.unpack_from("<i",IMG,i+1)[0]
            t=((IB+i+5+rel)&0xFFFFFFFF)-IB
            if plausible_entry(t): calls.append((i,"call" if b==0xE8 else "jmp",t))
        elif b==0xFF and IMG[i+1]==0x15:
            v=struct.unpack_from("<I",IMG,i+2)[0]; rva=v-IB
            if rva in IAT: calls.append((i,"call_iat",rva))
    return calls

def func_starts(calls):
    starts=set()
    for s,k,t in calls:
        if k=="call": starts.add(t)
    i=LO
    while i<HI:
        if IMG[i]==0xCC:
            j=i
            while j<LEN and IMG[j]==0xCC: j+=1
            if j-i>=3 and j<LEN: starts.add(j)
            i=j; continue
        if IMG[i]==0x55 and IMG[i+1]==0x8B and IMG[i+2]==0xEC: starts.add(i)
        i+=1
    return sorted(x for x in starts if LO<=x<LEN)

CALLS=build_call_sites()
STARTS=func_starts(CALLS)

def enc(x):
    k=bisect.bisect_right(STARTS,x)-1
    return STARTS[k] if k>=0 else None
def fend(x):
    k=bisect.bisect_right(STARTS,x)-1
    return STARTS[k+1] if (k>=0 and k+1<len(STARTS)) else None
UP=collections.defaultdict(list)
for s,k,t in CALLS:
    if k in ("call","jmp"): UP[t].append((s,k))
def callers_of_fn(fn):
    e=fend(fn) or fn; out=[]
    for t in range(fn,e+1): out.extend(UP.get(t,[]))
    return sorted(set(out))

ANCHORS={
 "gamestateupdate %d":0x9B4700,
 "EXE_CONFIGSTRINGMISMATCH":0x9B46E4,
 "ExpectedNetConfigStringMismatch":0x9B4D98,
 "EXE_LOSTRELIABLECOMMANDS":0x9BB5E8,
 "EXE_SERVERCOMMANDOVERFLOW":0x9BB584,
 "EXE_SERVERMESSAGEOVERFLOW":0x9BB5A0,
 "CA_GAMESTATE":0x9C0974,
 "EXE_AWAITINGGAMESTATE":0x9C5F1C,
 "process snapshots":0x9BEBD0,
 "CG_ServerCommand":0x9C61AD,
 "connectResponse":0x9BFF0C,
 "challengeResponse":0x9BFEE8,
 "connectReject":0x9BFEFC,
 "heartbeatresponse":0x9BFF1C,
 "statResponse":0x9BFF30,
 "disconnect_ack":0x9BFF40,
 "getchallenge 0 \"%s\"":0x9BFD04,
 "connect %s \"%s\"":0x9BFE28,
 "TQOS udp://%s:%d":0x985AB0,
}

report={
 "image": H.IMG, "image_sha256": H.sha256_file(H.IMG), "image_size": LEN,
 "imagebase": "0x%08X"%IB, "address_convention": "file_offset == RVA (recovered image)",
 "n_call_sites": len(CALLS), "n_func_starts": len(STARTS),
 "ws2_iat": {"0x%08X"%(IB+k):v for k,v in sorted(IAT.items())},
 "anchors":{}, "socket_api_functions":{}
}
for name,rva in ANCHORS.items():
    refs=H.refs_dword(IB+rva)
    handlers=[]
    for r in refs:
        f=enc(r)
        handlers.append({"xref":"0x%06X"%r,
                         "func":["0x%06X"%f,"0x%06X"%(fend(f) or 0)] if f else None,
                         "callers":["0x%06X"%s for s,_ in callers_of_fn(f)] if f else []})
    report["anchors"][name]={"va":"0x%08X"%(IB+rva),"rva":"0x%06X"%rva,
                             "string":H.cstr(rva,80),
                             "xrefs":["0x%06X"%r for r in refs],"handlers":handlers}

SOCK={}
for s,k,t in CALLS:
    if k=="call_iat" and IAT.get(t) in ("recv","recvfrom","select","send","sendto"):
        f=enc(s); SOCK.setdefault("0x%06X"%f,{}).setdefault(IAT[t],[]).append("0x%06X"%s)
report["socket_api_functions"]=SOCK

json.dump(report, open(os.path.join(OUT,"048_analysis.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)
print("calls=%d func_starts=%d anchors=%d socket_fns=%d" % (len(CALLS),len(STARTS),len(ANCHORS),len(SOCK)))
print("wrote evidence/048_analysis.json")


# ---------------- additional evidence artifacts ----------------

def emit():
    # call graph (direct + IAT) with function index
    cg={"image_sha256":H.sha256_file(H.IMG),
        "address_convention":"file_offset == RVA",
        "func_starts":STARTS,
        "iat":{hex(H.IB+k):v for k,v in sorted(IAT.items())},
        "calls":[[s,k,t] for s,k,t in CALLS]}
    json.dump(cg, open(os.path.join(OUT,"a050_callgraph.json"),"w",encoding="utf-8"))

    # named IAT slots (ws2_32 ordinals resolved from the on-disk exe)
    json.dump({"0x%08X"%(H.IB+k):v for k,v in sorted(IAT.items())},
              open(os.path.join(OUT,"s232_iat_named.json"),"w",encoding="utf-8"), indent=1)

    # function-start index (prologue + padding)
    json.dump(STARTS, open(os.path.join(OUT,"s20_funcstarts.json"),"w",encoding="utf-8"))

    # exports
    try:
        import pefile
        pe=pefile.PE(data=H._img, fast_load=True); pe.parse_data_directories()
        exp=[[ (e.name.decode("latin1") if e.name else None), e.ordinal, e.address] for e in pe.DIRECTORY_ENTRY_EXPORT.symbols]
    except Exception:
        exp=[]
    json.dump(exp, open(os.path.join(OUT,"s200_exports.json"),"w",encoding="utf-8"), indent=1)

    # long constant runs (coverage / holes)
    runs=[]; i=0; n=len(H._img)
    while i<n:
        j=i
        while j<n and H._img[j]==H._img[i]: j+=1
        if j-i>=32: runs.append([i,j-i,H._img[i]])
        i=j
    json.dump({"image_size":n,"n_long_runs":len(runs),
               "bytes_in_long_runs":sum(r[1] for r in runs),
               "long_runs":runs},
              open(os.path.join(OUT,"s520_coverage.json"),"w",encoding="utf-8"))

    # connectionless token table (with direction) - textual
    lines=["# connectionless token table (RVA, token, direction, first xref)",
           "# C2S = composed by client; S2C = compared by the 0x1C13A0 dispatcher"]
    for tok,rva,d,x in [
        ("getchallenge 0 \"%s\"",0x9BFD04,"C2S",0x1C071F),
        ("connect %s \"%s\"",0x9BFE28,"C2S",0x1C0D6F),
        ("heartbeat",0x9BFE40,"C2S",0x1C0EBC),
        ("stats",0x9BFE38,"C2S",0x1C0E27),
        ("challengeResponse",0x9BFEE8,"S2C",0x1C1685),
        ("connectReject",0x9BFEFC,"S2C",0x1C1756),
        ("connectResponse",0x9BFF0C,"S2C",0x1C17B5),
        ("heartbeatresponse",0x9BFF1C,"S2C",0x1C18B6),
        ("statResponse",0x9BFF30,"S2C",0x1C1964),
        ("disconnect_ack",0x9BFF40,"S2C",0x1C1B0B),
        ("echo",0x9BFF50,"S2C",0x1C1B4B),
        ("keyAuthorize",0x9BFF58,"S2C",0x1C1BC3),
        ("loadingnewmap",0x9BFF70,"S2C",0x1C1CAB),
        ("fastrestart",0x9BFF90,"S2C",0x1C1DF0)]:
        lines.append("0x%06X\t%s\t%s\t0x%06X" % (rva,tok,d,x))
    H.w("evidence/s520_tokentable.tsv", "\n".join(lines)+"\n")

    # disassembly dumps
    dumps={
     "d10_P5_recv_876ED0.txt": (0x876ED0,0x876F30,"P5 recv wrapper"),
     "d11_P5_send_876DB0.txt": (0x876DB0,0x876ED0,"P5 send wrapper"),
     "d12_873A00.txt":         (0x8739B0,0x873A40,"P5 recv entry 0x873A00"),
     "d20_1C13A0_dispatcher.txt": (0x1C13A0,0x1C15AB,"connectionless command dispatcher"),
     "d21_1C15AB_connectResponse.txt": (0x1C15AB,0x1C1D47,"connectResponse handler"),
     "d22_1BF300_oob_send.txt": (0x1BF300,0x1BF3E0,"OOB egress"),
     "d23_1C1EE0_connless_parse.txt": (0x1C1EE0,0x1C2170,"connectionless parser"),
     "d24_F2350_servercmd.txt": (0xF2350,0xF2900,"command/error dispatcher"),
     "d25_376A60_lostreliable.txt": (0x376A60,0x376B90,"EXE_LOSTRELIABLECOMMANDS reporter"),
     "d26_53760_host.txt": (0x53760,0x554C0,"gamestateupdate host"),
     "d27_37DBC0.txt": (0x37DBC0,0x37E480,"CA_GAMESTATE upstream"),
     "s11_P5_cluster.txt": (0x876800,0x877000,"P5 socket cluster"),
     "s12_P4_cluster.txt": (0x865300,0x866200,"P4 socket cluster"),
     "s13_TQOS_recv.txt": (0x87BA00,0x87BF80,"TQOS select+recv"),
     "s53_0F8FB0.txt": (0xF8FB0,0xF9240,"OOB pump"),
     "s160_1C2260.txt": (0x1C2170,0x1C24D0,"pump->parser bridge"),
     "s91_873E00.txt": (0x873D00,0x874200,"recvfrom consumer 0x873FC0"),
     "s130_621E50.txt": (0x621D90,0x622100,"packet dequeue"),
    }
    for fn,(a,b,t) in dumps.items():
        H.w("evidence/"+fn, H.dump(a,b,t))

    # network / protocol string inventory
    import re
    rx=re.compile(rb"[ -~]{4,}")
    KW=(b"NET_",b"SV_",b"CL_",b"MSG_",b"svc_",b"clc_",b"snapshot",b"Snapshot",b"gamestate",b"Gamestate",
        b"GameState",b"configstring",b"ConfigString",b"usercmd",b"UserCmd",b"ServerCommand",b"reliable",
        b"Reliable",b"packet",b"Packet",b"fragment",b"Fragment",b"challenge",b"Challenge",b"connectResponse")
    lines=[]
    for m in rx.finditer(H._img):
        st=m.group()
        if any(k in st for k in KW):
            lines.append("0x%06X\t%s" % (m.start(), st.decode("latin1")))
    H.w("evidence/s21_netstrings.txt", "\n".join(lines)+"\n")
    print("network strings:", len(lines))
    print("emitted: callgraph, iat names, funcstarts, exports, coverage, token table, %d dumps" % len(dumps))

emit()
print("evidence regeneration complete")

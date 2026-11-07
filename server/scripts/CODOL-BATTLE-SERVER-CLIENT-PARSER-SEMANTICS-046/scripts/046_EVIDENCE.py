# -*- coding: utf-8 -*-
"""046_EVIDENCE.py - regenerate the decisive 046 evidence. STRICTLY READ-ONLY."""
import sys, os, struct, re, json, hashlib
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _c046 as C
IB=C.IB
EV=C.EV
def W(name, txt): C.w(os.path.join(EV,name), txt)

def s(rva, ml=300):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")

# ---------- 1. input identity ----------
lines=["# 046 input + image identity"]
for p,lab in [(C.IMG,"S-IMG image_best.bin"),(C.EXE,"S-EXE codoMP_client_shipRetail.exe"),(C.DLL,"S-DLL ...Base.dll")]:
    lines.append("  %-34s %s  bytes=%d"%(lab, C.sha256_file(p), os.path.getsize(p)))
W("00_identity.txt", "\n".join(lines)+"\n")

# ---------- 2. the 045 chain function (TQOS attribution) ----------
out=["# 046-A  attribution of the 045 receive chain",
     "# image: image_best.bin sha256 17cef6e0..f045 ; ImageBase 0x400000 ; file_off == RVA",
     ""]
out.append("[A1] function containing 0x85D96E: 0x85D870..0x85DA82 (prologue push ebp;mov ebp,esp @0x85D870)")
out.append(C.dump(0x85D870,0x85DA82))
W("a10_chain_function.txt","\n".join(out)+"\n")

# ---------- 3. TQOS strings + xrefs ----------
out=["# 046-A  TQOS string evidence"]
for rva in (0x985A58,0x985A68,0x985A78,0x985A84,0x985A94,0x985AA4,0x985AB0,
            0x985ADF,0x985AFC,0x985B1C,0x985B38):
    out.append("  RVA 0x%06X VA 0x%08X  %r"%(rva,IB+rva,s(rva)))
out.append("")
out.append("[string xref: 'udp://%s:%d' VA 0x00D85AB0]")
out.append("  referenced from code at: 0x0085D7CB, 0x0085D89A  (both inside TQOS 0x85D5A0/0x85D870)")
W("a11_tqos_strings.txt","\n".join(out)+"\n")

# ---------- 4. TQOS class factory ----------
out=["# 046-A  TQOS package class factory (calls [0x87BFF0] with the TQOS type names)"]
out.append(C.dump(0x85D2E0,0x85D398))
out.append("")
out.append("[class-name strings pushed in this function]")
for va in (0xD85AA4,0xD85A94,0xD85A84,0xD85A78,0xD85A68,0xD85A58):
    out.append("   VA 0x%08X = %r"%(va,s(va-IB)))
out.append("")
out.append("[callers] 0x85D2E0 (QOSCSPkg factory) direct E8 callers: %s"%
           ", ".join("0x%X"%a for a,_ in C.e8_callers(0x85D2E0)))
W("a12_tqos_factory.txt","\n".join(out)+"\n")

# ---------- 5. call graph around the chain ----------
out=["# 046-A  call graph (E8 rel32) for the TQOS cluster functions"]
for nm,t in [("0x85D2E0 QOSCSPkg factory",0x85D2E0),("0x85D3A0 TQOS decode2-pkg",0x85D3A0),
             ("0x85D430 TQOS send",0x85D430),("0x85D500",0x85D500),("0x85D5A0 TQOS init",0x85D5A0),
             ("0x85D870 TQOS recv",0x85D870),("0x85DAF0",0x85DAF0),("0x85E6F0 TQOS dispatch",0x85E6F0),
             ("0x85E9C0 TQOS",0x85E9C0),("0x85EB50 tqos_create_protohandle",0x85EB50),
             ("0x87BA50 thunk",0x87BA50),("0x87BE00 select+recv",0x87BE00),
             ("0x87C110 tdr-unpack1",0x87C110),("0x87D5A0 tdr-unpack2",0x87D5A0)]:
    cs=C.e8_callers(t)
    out.append("  %-34s : %s"%(nm, ", ".join("0x%X(%s)"%(a,k) for a,k in cs) or "(none)"))
W("a13_callgraph.txt","\n".join(out)+"\n")

# ---------- 6. TDR net strings + xrefs ----------
out=["# 046-B  TDR (Tencent Data Representation) net-buffer diagnostics"]
pat=re.compile(rb"[ -~]{10,}")
n=0
for m in pat.finditer(C._img):
    st=m.group().decode("latin1")
    if ("net-buffer" in st) or ("tdr_net.c" in st) or ("host-buffer" in st):
        out.append("  RVA 0x%06X %r"%(m.start(),st)); n+=1
out.append("  (total %d)"%n)
out.append("")
out.append("[direct VA xref of the tdr_net.c string  VA 0x00D9F060 = RVA 0x99F060]")
va=IB+0x99F060; refs=[]; i=C._img.find(struct.pack("<I",va))
while i>=0: refs.append(i); i=C._img.find(struct.pack("<I",va),i+1)
out.append("  refs: "+", ".join("0x%08X"%r for r in refs))
out.append("  => 0x87C365, 0x87D2EF, 0x87D3C7, 0x87EB5A are all inside the 0x87C110 / 0x87D5A0 family")
W("a14_tdr_strings.txt","\n".join(out)+"\n")

# ---------- 7. ws2_32 IAT usage ----------
ORD={1:"accept",2:"bind",3:"closesocket",4:"connect",5:"getpeername",6:"getsockname",
 7:"getsockopt",10:"ioctlsocket",12:"inet_ntoa",13:"listen",14:"ntohl",15:"ntohs",
 16:"recv",17:"recvfrom",18:"select",19:"send",20:"sendto",21:"setsockopt",22:"shutdown",
 23:"socket",52:"gethostbyname",111:"WSAGetLastError",115:"WSAStartup",116:"WSACleanup",
 151:"__WSAFDIsSet",8:"htonl",9:"htons",112:"ord112",57:"ord57"}
out=["# 046-A/E  every code site that calls through the ws2_32 ordinal IAT (0xCA8400..0xCA8700)"]
targets={"send":0xCA84E0,"recv":0xCA84E4,"select":0xCA84E8,"connect":0xCA84F0,
         "sendto":0xCA8518,"recvfrom":0xCA851C,"socket":0xCA8548,"bind":0xCA8554,
         "listen":0xCA84FC,"accept":0xCA8500,"closesocket":0xCA8544,"ioctlsocket":0xCA8540}
for nm,va in targets.items():
    sites=[]
    for i in range(0x1000,0x8a7000-6):
        if C._img[i]==0xFF and C._img[i+1] in (0x15,0x25) and struct.unpack_from("<I",C._img,i+2)[0]==va:
            sites.append(i)
    out.append("  %-10s slot VA 0x%08X : %s"%(nm,va,", ".join("0x%X"%x for x in sites)))
W("a15_ws2_iat_usage.txt","\n".join(out)+"\n")

# ---------- 8. game-protocol strings + xrefs ----------
out=["# 046-B/E  engine game-protocol strings and their code xrefs (separate code region from TQOS)"]
for nm,rva in [("gamestateupdate %d",0x9B4700),("CA_GAMESTATE",0x9C0974),
               ("EXE_AWAITINGGAMESTATE",0x9C5F1C),("EXE_LOSTRELIABLECOMMANDS",0x9BB5E8),
               ("EXE_SERVERCOMMANDOVERFLOW",0x9BB584),("connectResponse",0x9BFF0C),
               ("EXE_CONFIGSTRINGMISMATCH",0x9B46E4),("EXE_ERR_RELIABLE_CYCLED_OUT",0x9C61C0)]:
    va=IB+rva; refs=[]; i=C._img.find(struct.pack("<I",va))
    while i>=0: refs.append(i); i=C._img.find(struct.pack("<I",va),i+1)
    out.append("  %-32s VA 0x%08X refs: %s"%(nm,va,", ".join("0x%08X"%r for r in refs) or "NONE"))
W("a16_game_strings.txt","\n".join(out)+"\n")

# ---------- 9. decoders 0x87C110 / 0x87D5A0 argument prologue ----------
out=["# 046-B  decoder 0x87C110 / 0x87D5A0 prologue (argument capture)"]
out.append(C.dump(0x87C110,0x87C160,"0x87C110"))
out.append(C.dump(0x87D5A0,0x87D5F0,"0x87D5A0"))
W("a17_decoder_prologue.txt","\n".join(out)+"\n")

print("evidence written to", EV)
for f in sorted(os.listdir(EV)): print("  ",f, os.path.getsize(os.path.join(EV,f)))

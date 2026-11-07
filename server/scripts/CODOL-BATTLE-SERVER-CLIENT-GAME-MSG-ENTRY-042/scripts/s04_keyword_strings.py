# -*- coding: utf-8 -*-
"""Search for non-Winsock transport / dispatch primitives and WKNet-layer strings.
Read-only."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C

# 1. WKNet / kernel-net related strings in .rdata/.data
def itersec(name):
    s=[x for x in C.SECTIONS if x["name"]==name][0]
    return s
def strings_in(name, minlen=6):
    s=itersec(name)
    data=C._b[s["raw"]:s["raw"]+s["rsize"]]
    out=[]; i=0; cur=bytearray(); start=0
    while i < len(data):
        c=data[i]
        if 32<=c<127:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen:
                out.append((s["va"]+start, cur.decode("latin1")))
            cur=bytearray()
        i+=1
    return out

KW = ["WKNet","KernelBind","KernelConnect","KernelDisconnect","SendPacket","RecvPacket",
      "wk_ip_config","wkconfig","netchan","NetChan","NETCHAN","opcode","Opcode","OPCODE",
      "svc_","clc_","Gamestate","gamestate","configstring","Configstring","CONFIGSTRING",
      "com_","CG_","SV_","CL_","MSG_","handler","dispatch","Dispatch","recv","Recv"]
hits=[]
for sec in (".rdata",".data"):
    for va,s in strings_in(sec, 4):
        for k in KW:
            if k in s:
                hits.append((va,sec,s)); break
out=["RVA\tSECTION\tSTRING"]
for va,sec,s in sorted(hits):
    out.append("%08x\t%s\t%s" % (va, sec, s[:160]))
open(os.path.join(C.EV,"keyword_strings.tsv"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("keyword strings found:", len(hits))
for va,sec,s in sorted(hits)[:80]:
    try: print("  %08x %-8s %s" % (va,sec,s[:110]))
    except Exception: pass

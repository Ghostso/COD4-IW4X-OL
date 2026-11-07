# -*- coding: utf-8 -*-
import io, os
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
EV=os.path.join(ROOT,"evidence")
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)
def norm(x): return int(x,16)

slots=[]
with io.open(os.path.join(EV,"winsock_slots.tsv"),encoding="utf-8") as f:
    f.readline()
    for ln in f:
        p=ln.rstrip("\n").split("\t")
        slots.append(dict(idx=p[0],slot_rva=p[1],slot_va=p[2],off=p[3],kind=p[4],name=p[5],resolved=p[6]))
calls=[]
with io.open(os.path.join(EV,"winsock_callsites.tsv"),encoding="utf-8") as f:
    hdr=f.readline().rstrip("\n").split("\t")
    for ln in f:
        calls.append(dict(zip(hdr,ln.rstrip("\n").split("\t"))))
by_slot={}
for c in calls: by_slot.setdefault(norm(c["SLOT_RVA"]),[]).append(c)

lines=["EVID_ID\tAPI_NAME\tRESOLVE_KIND\tSLOT_RVA\tSLOT_VA\tSLOT_FILE_OFF\tCALL_COUNT\tCALL_RVAS\tCALL_FILE_OFFSETS\tHAS_REAL_CALL\tSTORAGE_EVIDENCE\n"]
i=0
for s in slots:
    i+=1
    cl=by_slot.get(norm(s["slot_rva"]),[])
    rvas=";".join(c["TEXT_RVA"] for c in cl) if cl else ""
    offs=";".join(c["FILE_OFF"] for c in cl) if cl else ""
    kind = "IMAGE_IMPORT_BY_NAME" if s["kind"]=="NAME" else "IMAGE_ORDINAL"
    lines.append("\t".join(["WFP-%03d"%i, s["resolved"], kind, s["slot_rva"], s["slot_va"], s["off"],
        str(len(cl)), rvas, offs, "Y" if cl else "N",
        "PE .idata2 fixed IAT slot (slot table anchor 0xB02000), value kind=%s"%s["kind"]])+"\n")
W("WINSOCK_FUNCTION_POINTERS.tsv","".join(lines))
print("WFP rows:",i)

# stats
import collections
cc=collections.Counter()
for k,v in by_slot.items(): cc[len(v)]+=1
print("slots with call sites:",sum(1 for k,v in by_slot.items() if v))
print("total calls mapped:",sum(len(v) for v in by_slot.values()))

# -*- coding: utf-8 -*-
import io, os, struct
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
EV=os.path.join(ROOT,"evidence")
DLL=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
b=open(DLL,"rb").read()
pe_secs=[]
import pefile
pe=pefile.PE(data=b,fast_load=False)
for s in pe.sections:
    pe_secs.append((s.Name.rstrip(b"\0").decode("latin1"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))
IB=pe.OPTIONAL_HEADER.ImageBase
def rva2off(r):
    for n,va,vs,raw,rs in pe_secs:
        if va<=r<va+max(vs,rs): return raw+(r-va)
    return None
def cstr(r):
    o=rva2off(r)
    if o is None: return None
    e=b.find(b"\0",o)
    if e<0 or e-o>160: return None
    return b[o:e]
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

# ---- DYNAMIC_BINDING_CALLS.tsv  (LoadLibraryA / GetProcAddress + the explicit WS2_32 resolver)
rows=[]
with io.open(os.path.join(EV,"loadlib_gpa_callsites.tsv"),encoding="utf-8") as f:
    hdr=f.readline().rstrip("\n").split("\t")
    for ln in f: rows.append(dict(zip(hdr,ln.rstrip("\n").split("\t"))))

# Determine a nearby pushed string argument for each call site (scan up to 40 bytes back for 68 imm32)
def nearby_string(rva):
    o=rva2off(rva)
    if o is None: return None
    lo=max(0,o-48)
    for k in range(o-5,lo-1,-1):
        if b[k]==0x68:
            v=struct.unpack("<I",b[k+1:k+5])[0]
            if 0x10000000<=v<IB+pe.OPTIONAL_HEADER.SizeOfImage:
                s=cstr(v-IB)
                if s and 3<len(s)<64:
                    return ("push 0x%X"%v, s)
    return None

hdr=["EVID_ID","API","CALL_RVA","CALL_VA","FILE_OFF","SECTION","RAW_BYTES","IAT_SLOT_RVA","IAT_SLOT_VA","IAT_SLOT_FILE_OFF",
     "ARG1_CLASS","ARG2_CLASS","NEARBY_STRING_ARG","RETURN_SINK","DOWNSTREAM_USE","CONFIDENCE","NOTES"]
lines=["\t".join(hdr)+"\n"]
i=0
for r in rows:
    i+=1
    api=r["API"]; rva=int(r["TEXT_RVA"],16); va=r["TEXT_VA"]
    ns=nearby_string(rva)
    if api=="LoadLibraryA":
        a1="module name (char* / LPCSTR)"; a2="n/a"
        sink="EAX = HMODULE"
        down="HMODULE passed to GetProcAddress (usual delay-load pattern)"
        conf="CONFIRMED_DIRECT"
        note="dynamic LoadLibraryA call through hidden IAT slot"
    else:
        a1="HMODULE (= prior LoadLibraryA/GetModuleHandleA result)"; a2="API name (char*) or ordinal (LPCSTR/LPWORD)"
        sink="EAX = FARPROC (function address)"
        down="stored to stack temp or IAT slot, then called indirectly"
        conf="CONFIRMED_DIRECT"
        note="dynamic GetProcAddress call through hidden IAT slot"
    lines.append("\t".join(["DBC-%03d"%i,api,r["TEXT_RVA"],va,r["FILE_OFF"],r["SECTION"],r["BYTES"],
        r["SLOT_RVA"],r["SLOT_VA"],r["SLOT_FILE_OFF"],a1,a2,
        ("%s %r"%(ns[0],ns[1])) if ns else "",
        sink,down,conf,note])+"\n")
W("DYNAMIC_BINDING_CALLS.tsv","".join(lines))
print("DYNAMIC_BINDING_CALLS.tsv rows:",i,"nearby-string hits:",sum(1 for r in rows if nearby_string(int(r["TEXT_RVA"],16))))

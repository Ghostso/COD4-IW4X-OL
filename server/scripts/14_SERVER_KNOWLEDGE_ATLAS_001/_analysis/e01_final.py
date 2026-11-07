import json
NEW=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
O13=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_1113.json"
OLD=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_OLD.json"
def load(p):
    j=json.load(open(p,encoding="utf-8")); d={}
    for s in j["symbols"]:
        if s.get("section")==".text" and s.get("type",0)!=0:
            d[s["name"]]=int(s["rva"])
    return d
n=load(NEW); o=load(O13); od=load(OLD)
print("=== E-01: function-name set comparison ===")
for lbl,a in (("2697",n),("1113",o),("OLD",od)):
    print("  %-5s .text funcs = %d" % (lbl,len(a)))
def jac(a,b):
    i=len(set(a)&set(b))
    return i, i/(len(set(a)|set(b)))
for x,y,lbl in [(n,o,"2697 vs 1113"),(n,od,"2697 vs OLD"),(o,od,"1113 vs OLD")]:
    i,j=jac(x,y); print("  %-14s shared=%6d  Jaccard=%.1f%%" % (lbl,i,100*j))
print()
print("=== engine-symbol presence matrix (the shared skeleton) ===")
keys=["_Com_Init","_Com_Frame","_SV_Init","_SV_Frame","_SV_DirectConnect","_SV_ClientEnterWorld",
      "_SV_SendClientGameState","_SV_SendClientSnapshot","_SV_WriteSnapshotToClient",
      "_MSG_WriteByte","_MSG_WriteShort","_MSG_WriteLong","_MSG_WriteBits","_MSG_WriteDeltaEntity",
      "_Netchan_Transmit","_Netchan_Process","_Huffman_InitMain","_Cvar_Init","_Sys_Main",
      "_CODOL_NetchanProcess","_CODOL_WriteGamestate","_CODOL_WriteConfigstrings",
      "_SV_WriteReliableCommand","_SV_ProfileCommand2697","_CODOL2697_WriteGamestate",
      "_CODOL2697_WriteSnapshot","_CODOL2697_ReadRegistration","_CODOL2697_WriteConfigstrings"]
print("  %-34s %-11s %-11s %-11s" % ("symbol","2697","1113","OLD"))
for k in keys:
    f=lambda d: ("0x%X"%d[k]) if k in d else "-"
    print("  %-34s %-11s %-11s %-11s" % (k,f(n),f(o),f(od)))
print()
print("=== shared-but-different-RVA check (same name, different RVA) ===")
same=sum(1 for k in n if k in o and n[k]==o[k]); both=len(set(n)&set(o))
print("  both present=%d ; same RVA=%d (%.2f%%)" % (both,same,100.0*same/both))
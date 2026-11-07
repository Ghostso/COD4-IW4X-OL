import json, pefile
sym=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json",encoding="utf-8"))
want=["_CODOL2697_WriteConfigstrings","_CODOL_WriteConfigstrings","_CODOL2697_WriteGamestate","_SV_WriteClientSnapshot","_SV_SendClientSnapshot"]
rvas={s["name"]:int(s["rva"]) for s in sym["symbols"] if s["name"] in want and s.get("section")==".text"}
for k in want: print("  SERVER symbol %-32s %s" % (k, ("RVA 0x%X"%rvas[k]) if k in rvas else "ABSENT"))
print()
# Is there ANY symbol in CLIENT near A0807? client has no symbols; use recovered image only.
print("NOTE: client recovered image has no symbol table -> cannot name client functions; must use boundaries by prologue/padding analysis.")
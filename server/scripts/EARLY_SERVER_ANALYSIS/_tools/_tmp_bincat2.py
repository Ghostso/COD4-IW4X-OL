import csv, os, json
base = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS"
man = {}
with open(os.path.join(base,"00_BASELINE","EARLY_SERVER_00_FILE_MANIFEST.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f): man[r["relpath"]] = r
pe = {}
with open(os.path.join(base,"01_ASSET_MAP","EARLY_SERVER_01_PE_CATALOG.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f): pe[r["relpath"]] = r

# role/duty annotations derived from evidence (kept factual, citing import of codol_dedrun.exe for plugins)
roles = {
 "dedicated\\bin\\codol_dedrun.exe": ("game-server", "CoD4x fork native dedicated server for CoDOL 1.1.1.13 (AGPL3). 185 Plugin_* exports.", "CONFIRMED"),
 "dedicated\\bin\\codol_dedrun_next.exe": ("game-server", "Byte-identical duplicate of codol_dedrun.exe (same SHA-256); deployment/live copy.", "CONFIRMED"),
 "dedicated\\bin\\pexports.exe": ("tool", "PE export-table dumper (third-party 0.47). Not a game component.", "CONFIRMED"),
 "Kernel33.dll": ("client-patch", "CoDOL client patch DLL (GetProcAddress/LoadLibraryA shim). 10.19 MiB .rsrc.", "CONFIRMED"),
 "patcher\\Kernel33.dll": ("client-patch", "Same DLL as root Kernel33.dll (same SHA-256); source repo copy.", "CONFIRMED"),
 "dedicated\\plugins\\censor\\censor.dll": ("plugin", "Server plugin; imports codol_dedrun.exe.", "CONFIRMED"),
 "dedicated\\plugins\\example_cpp_plugin\\cpptest_plugin.dll": ("plugin", "Example C++ server plugin.", "CONFIRMED"),
 "dedicated\\plugins\\iw4ol_b3hide\\b3hide.dll": ("plugin", "Server plugin (B3 hide).", "CONFIRMED"),
 "dedicated\\plugins\\legacybanlist\\legacybanlist.dll": ("plugin", "Ban-list plugin.", "CONFIRMED"),
 "dedicated\\plugins\\pchat\\pchat.dll": ("plugin", "Chat plugin.", "CONFIRMED"),
 "dedicated\\plugins\\screenshotsender\\nehoscreenshotuploader.dll": ("plugin", "Screenshot upload plugin.", "CONFIRMED"),
 "dedicated\\plugins\\simplebanlist\\simplebanlist.dll": ("plugin", "Ban-list plugin.", "CONFIRMED"),
 "dedicated\\plugins\\sourcebansplugin\\sourcebansplugin.dll": ("plugin", "SourceBans plugin.", "CONFIRMED"),
 "dedicated\\plugins\\warn\\warn.dll": ("plugin", "Warning plugin.", "CONFIRMED"),
}
order = ["relpath","size","sha256","arch","imagebase","entrypoint_rva","timestamp","is_dll",
         "import_modules","import_count","export_count","version_file","version_product","role","duty","evidence_level"]
out = os.path.join(base,"01_ASSET_MAP","EARLY_SERVER_01_BINARY_CATALOG.csv")
with open(out,"w",newline="",encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(order)
    for rel in sorted(roles, key=lambda x: (x.startswith("dedicated\\plugins"), x)):
        r = pe.get(rel); m = man.get(rel)
        if not r:
            print("MISSING PE ROW", rel); continue
        role, duty, lvl = roles[rel]
        w.writerow([rel, r["size"], m["sha256"] if m else "", r["arch"], r["imagebase"], r["entrypoint_rva"],
                    r["timestamp"], r["is_dll"], r["import_modules"], r["import_count"], r["export_count"],
                    r.get("version_file",""), r.get("version_product",""), role, duty, lvl])
print("rows:", len(roles), "->", out)

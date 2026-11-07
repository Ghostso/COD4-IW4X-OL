import csv, os, json
base = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS"
manifest = {}
with open(os.path.join(base, "00_BASELINE", "EARLY_SERVER_00_FILE_MANIFEST.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        manifest[row["relpath"]] = row
pe = {}
with open(os.path.join(base, "01_ASSET_MAP", "EARLY_SERVER_01_PE_CATALOG.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        pe[row["relpath"]] = row
print("MANIFEST COLS", list(next(iter(manifest.values())).keys()))
want_sub = ["dedicated\\bin\\codol_dedrun", "dedicated\\bin\\codol_dedrun_next", "patcher\\Kernel33.dll",
            "dedicated\\plugins", "dedicated\\bin\\pexports", "codol_dedrun"]
for rel in sorted(pe):
    low = rel.lower()
    if any(k in low for k in ["dedicated\\bin\\", "dedicated\\plugins\\", "patcher\\", "lobby\\", "build\\"]):
        pass
# Just print candidate server-related PEs
keys = ["codol_dedrun", "kernel33", "pexports", "censor.dll", "cpptest_plugin", "b3hide", "legacybanlist",
        "pchat.dll", "nehoscreenshotuploader", "simplebanlist", "sourcebansplugin", "warn.dll"]
for rel in sorted(pe):
    low = rel.lower()
    if any(k in low for k in keys):
        r = pe[rel]
        sha = manifest.get(rel, {}).get("sha256", "")
        print("|".join([rel, r["size"], r["arch"], r["imagebase"], r["entrypoint_rva"], r["is_dll"],
                        str(r["import_count"]), str(r["export_count"]), sha, r["import_modules"]]))

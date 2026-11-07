import json

targets = [
    "cbuf_addtext", "cmd_executesinglecommand", "sv_spawnserver", 
    "sv_map", "cl_map", "cl_startlocalserver", "sv_init", 
    "sv_startup", "cmd_addcommand", "com_frame", "cl_frame", 
    "scr_updatescreen", "localmatch", "startlocalserver",
    "map_f", "devmap_f", "spawntraining", "startmatch"
]

for name, path in [
    ("syms_1113", r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_1113.json"),
    ("syms_NEW", r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"),
]:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    syms = d.get('symbols', [])
    print(f"=== {name} total symbols: {len(syms)} ===")
    for s in syms:
        sname = s.get('name', '')
        sname_lower = sname.lower()
        for t in targets:
            if t in sname_lower:
                va = s.get('va', 0)
                rva = s.get('rva', 0)
                print(f"  [{name}] {sname} -> VA: 0x{va:X}, RVA: 0x{rva:X}")

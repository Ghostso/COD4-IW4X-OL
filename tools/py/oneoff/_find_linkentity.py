import json

for name, path in [
    ("syms_1113", r"CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_1113.json"),
    ("syms_NEW", r"CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"),
]:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    syms = d.get('symbols', [])
    for s in syms:
        sname = s.get('name', '')
        if 'linkentity' in sname.lower() or 'sv_link' in sname.lower():
            va = s.get('va', 0)
            rva = s.get('rva', 0)
            print(f"[{name}] {sname} -> VA: 0x{va:X}, RVA: 0x{rva:X}")

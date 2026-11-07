import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

s = s.replace('STAMP = "20260928_1900"', 'STAMP = "20260928_2015"', 1)

old = '''    "IFS1_ELEVATED_20260928_181937",  # 204-byte frame accepted
]'''
new = '''    "IFS1_ELEVATED_20260928_181937",  # 204-byte frame accepted
    # ---- BREAKTHROUGH: DW_LOBBY_CONNECTED / DWLOBBY_PUMP_SUCCESS ----
    "IFS1_ELEVATED_20260928_182932",  # uA50=4 DW_LOBBY_CONNECTED held 60 s
    "IFS1_ELEVATED_20260928_183320",  # uA50=5 DWLOBBY_PUMP_SUCCESS, TPFUI SystemSetting
]'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old2 = '''    "CODOLServer/logs/PLAIN/frame204b_20260928_181807.jsonl",
]'''
new2 = '''    "CODOLServer/logs/PLAIN/frame204b_20260928_181807.jsonl",
    "CODOLServer/logs/PLAIN/hold_20260928_183208.jsonl",
    "run_codol_001/runs/IFS1_ELEVATED_20260928_183320/iips_files/TenioLog/20260928_183329.log",
    "CODOLServer/archive/CONFIRMED_20260928_1900/CHECKSUMS.txt",
]'''
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")

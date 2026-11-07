import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

s = s.replace('STAMP = "20260928_2045"', 'STAMP = "20260928_2115"', 1)

old = '''    "IFS1_ELEVATED_20260928_183320",  # uA50=5 DWLOBBY_PUMP_SUCCESS, TPFUI SystemSetting
]'''
new = '''    "IFS1_ELEVATED_20260928_183320",  # uA50=5 DWLOBBY_PUMP_SUCCESS, TPFUI SystemSetting
    # ---- 20260928 reproduction: 3/3 consecutive successes ----
    "IFS1_ELEVATED_20260928_184705",
    "IFS1_ELEVATED_20260928_184933",
    "IFS1_ELEVATED_20260928_185158",
]'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old2 = '''    "CODOLServer/archive/CONFIRMED_20260928_2015/CHECKSUMS.txt",
]'''
new2 = '''    "CODOLServer/archive/CONFIRMED_20260928_2015/CHECKSUMS.txt",
    "CODOLServer/archive/CONFIRMED_20260928_2045/CHECKSUMS.txt",
    "CODOLServer/LOBBY_BREAKTHROUGH_REPRO_20260928.md",
    "CODOLServer/logs/PLAIN/repro_20260928_184532.jsonl",
]'''
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")

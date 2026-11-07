import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

s = s.replace('STAMP = "20260928_2115"', 'STAMP = "20260928_2135"', 1)

old = '''    "IFS1_ELEVATED_20260928_185158",
]'''
new = '''    "IFS1_ELEVATED_20260928_185158",
    # ---- dialog body captured: "与大厅服务失去连接" ----
    "IFS1_ELEVATED_20260928_190708",
    "IFS1_ELEVATED_20260928_191742",
]'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old2 = '''    "CODOLServer/logs/PLAIN/repro_20260928_184532.jsonl",
]'''
new2 = '''    "CODOLServer/logs/PLAIN/repro_20260928_184532.jsonl",
    "CODOLServer/logs/PLAIN/dlg2_20260928_190535.jsonl",
    "CODOLServer/_mainline/_fatal_dialog_probe.py",
    "CODOLServer/archive/CONFIRMED_20260928_2115/CHECKSUMS.txt",
]'''
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")

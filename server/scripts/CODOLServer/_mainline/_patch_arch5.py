import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()
s = s.replace('STAMP = "20260928_2015"', 'STAMP = "20260928_2045"', 1)

old = '''    "CODOLServer/archive/CONFIRMED_20260928_1900/CHECKSUMS.txt",
]'''
new = '''    "CODOLServer/archive/CONFIRMED_20260928_1900/CHECKSUMS.txt",
    "CODOLServer/archive/CONFIRMED_20260928_2015/CHECKSUMS.txt",
    "CODOLServer/archive/CONFIRMED_20260928_2045/CHECKSUMS.txt",
]'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")

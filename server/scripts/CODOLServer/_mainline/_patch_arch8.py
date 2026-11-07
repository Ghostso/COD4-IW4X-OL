import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()
s = s.replace('STAMP = "20260928_2135"', 'STAMP = "20260928_2155"', 1)
old = '    "IFS1_ELEVATED_20260928_191742",\n]'
new = ('    "IFS1_ELEVATED_20260928_191742",\n'
       '    # ---- type-byte / multi-frame experiments ----\n'
       '    "IFS1_ELEVATED_20260928_192251",\n'
       '    "IFS1_ELEVATED_20260928_192553",\n]')
assert s.count(old) == 1
s = s.replace(old, new, 1)
old2 = '    "CODOLServer/archive/CONFIRMED_20260928_2115/CHECKSUMS.txt",\n]'
new2 = ('    "CODOLServer/archive/CONFIRMED_20260928_2115/CHECKSUMS.txt",\n'
        '    "CODOLServer/archive/CONFIRMED_20260928_2135/CHECKSUMS.txt",\n'
        '    "CODOLServer/logs/PLAIN/type2_20260928_192230.jsonl",\n'
        '    "CODOLServer/logs/PLAIN/multi_20260928_192535.jsonl",\n]')
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")

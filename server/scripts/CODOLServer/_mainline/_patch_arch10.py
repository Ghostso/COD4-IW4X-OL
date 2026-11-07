import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()
s = s.replace('STAMP = "20260928_2155"', 'STAMP = "20260928_2215"', 1)
old = '    "IFS1_ELEVATED_20260928_192553",\n]'
new = ('    "IFS1_ELEVATED_20260928_192553",\n'
       '    # ---- codec internals sampled ----\n'
       '    "IFS1_ELEVATED_20260928_193046",\n'
       '    "IFS1_ELEVATED_20260928_193625",\n]')
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
old2 = '    "CODOLServer/logs/PLAIN/multi_20260928_192535.jsonl",\n]'
new2 = ('    "CODOLServer/logs/PLAIN/multi_20260928_192535.jsonl",\n'
        '    "CODOLServer/archive/CONFIRMED_20260928_2155/CHECKSUMS.txt",\n'
        '    "CODOLServer/logs/PLAIN/codec_20260928_193035.jsonl",\n'
        '    "CODOLServer/logs/PLAIN/codec2_20260928_193323.jsonl",\n]')
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
